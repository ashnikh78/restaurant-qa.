import warnings
warnings.filterwarnings("ignore", message='Field "model_name" has conflict with protected namespace "model_".*')

import os
import time
import random
import hashlib
import requests
import backoff
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from fake_useragent import UserAgent
from fake_useragent.errors import FakeUserAgentError
from pathlib import Path
from loguru import logger
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Set
from config import AppConfig
from pipeline import PipelineError
from tqdm import tqdm

load_dotenv()  # ✅ Load env vars from .env

class CrawlerService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = Path(config.data_dir)
        self.chroma_db_dir = config.chroma_db_dir
        self.base_url = "https://www.hdbfs.com/"
        self.processed_urls: Set[str] = set()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

        self.data_dir.mkdir(exist_ok=True)
        Path(self.chroma_db_dir).mkdir(exist_ok=True)

        self._initialize_embeddings()
        self._initialize_vectorstore()

        logger.info("✅ CrawlerService initialized successfully")

    def _initialize_embeddings(self):
        try:
            model_path = "sentence-transformers/all-MiniLM-L6-v2"
            logger.info(f"🔄 Loading embedding model: {model_path}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("✅ Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise PipelineError(f"Embedding model initialization failed: {e}")

    def _initialize_vectorstore(self):
        try:
            self.vectorstore = Chroma(
                persist_directory=self.chroma_db_dir,
                embedding_function=self.embeddings,
                collection_name="loan_hdfs"
            )
            logger.info("✅ Vector store initialized")
        except Exception as e:
            logger.error(f"❌ Vector store initialization failed: {e}")
            raise PipelineError(f"Vector store initialization failed: {e}")

    def _get_user_agent(self) -> str:
        try:
            return UserAgent().random
        except Exception:
            fallback = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/117.0"
            logger.warning("⚠️ Failed to generate User-Agent dynamically. Using fallback.")
            return fallback

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        jitter=backoff.full_jitter
    )
    def _fetch_page(self, url: str) -> str:
        headers = {
            "User-Agent": self._get_user_agent(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }

        try:
            logger.info(f"🌐 Fetching URL: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.warning(f"⚠️ Status 404 from {url} — skipping.")
                return None
            else:
                logger.warning(f"⚠️ Status {response.status_code} from {url}")
                raise PipelineError(f"Unexpected status {response.status_code} from {url}")
        except Exception as e:
            logger.warning(f"⚠️ Error fetching {url}: {e}")
            raise e

        raise PipelineError(f"Failed to fetch URL after retries: {url}")

    def _extract_text(self, html: str, url: str) -> str:
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "iframe"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            title = soup.title.string.strip() if soup.title else ""
            cleaned_text = f"{title}\n\n" + "\n".join(lines)
            logger.info(f"📝 Extracted {len(cleaned_text)} characters from {url}")
            return cleaned_text
        except Exception as e:
            logger.error(f"❌ Error extracting text from {url}: {e}")
            return ""

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _save_text_to_file(self, text: str, url: str) -> Path | None:
        try:
            filename = url.replace(self.base_url, "").replace("/", "_").strip("_") or "index"
            file_path = self.data_dir / f"{filename}.txt"
            new_hash = self._hash_content(text)

            if file_path.exists():
                with file_path.open("r", encoding="utf-8") as f:
                    if self._hash_content(f.read()) == new_hash:
                        logger.info(f"⏭️ Skipping unchanged content for {url}")
                        return None

            with file_path.open("w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"💾 Saved content to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ Failed to save content for {url}: {e}")
            raise PipelineError(f"Failed to save text: {e}")

    def _load_and_store_document(self, file_path: Path | None) -> None:
        try:
            if not file_path:
                return
            loader = TextLoader(str(file_path), encoding="utf-8")
            documents = loader.load()
            for doc in documents:
                doc.metadata.update({
                    "source": str(file_path),
                    "filename": file_path.name,
                    "file_type": ".txt",
                    "processed_at": time.time()
                })
            split_docs = self.text_splitter.split_documents(documents)
            self.vectorstore.add_documents(split_docs)
            self.vectorstore.persist()
            logger.info(f"📦 Stored {len(split_docs)} chunks from {file_path.name}")
        except Exception as e:
            logger.error(f"❌ Failed to store document: {e}")
            raise PipelineError(f"Failed to store document: {e}")

    def crawl_and_build_knowledge_base(self, max_pages: int = 10) -> None:
        try:
            seed_urls = [
                self.base_url,
                f"{self.base_url}products/personal-loan",
                f"{self.base_url}products/business-loan",
                f"{self.base_url}faqs",
                f"{self.base_url}contact-us"
            ]
            urls_to_crawl = seed_urls[:]
            crawled_urls = set()
            pbar = tqdm(total=max_pages, desc="🔎 Crawling", ncols=100)

            while urls_to_crawl and len(crawled_urls) < max_pages:
                url = urls_to_crawl.pop(0)
                if url in crawled_urls or not url.startswith(self.base_url):
                    continue
                html = self._fetch_page(url)
                if html is None:
                    crawled_urls.add(url)  # Avoid retrying
                    pbar.update(1)
                    continue
                text = self._extract_text(html, url)
                if not text or len(text.split()) < 50:
                    continue
                file_path = self._save_text_to_file(text, url)
                self._load_and_store_document(file_path)
                crawled_urls.add(url)
                self.processed_urls.add(url)
                pbar.update(1)

                soup = BeautifulSoup(html, "html.parser")
                for link in soup.find_all("a", href=True):
                    full_url = urljoin(self.base_url, link["href"])
                    if (urlparse(full_url).netloc == urlparse(self.base_url).netloc and
                        full_url not in crawled_urls and
                        full_url not in urls_to_crawl):
                        urls_to_crawl.append(full_url)

                time.sleep(random.uniform(1.0, 2.5))  # Human-like wait time

            pbar.close()
            logger.info(f"✅ Successfully crawled {len(crawled_urls)} pages")
        except Exception as e:
            logger.error(f"❌ Crawling failed: {e}")
            raise PipelineError(f"Crawling failed: {e}")

    def get_processed_urls(self) -> List[str]:
        return list(self.processed_urls)

    def clear_knowledge_base(self) -> None:
        try:
            self.vectorstore.delete_collection()
            self.vectorstore = Chroma(
                persist_directory=self.chroma_db_dir,
                embedding_function=self.embeddings,
                collection_name="loan_hdfs"
            )
            self.processed_urls.clear()
            for file_path in self.data_dir.glob("*.txt"):
                file_path.unlink()
            logger.info("🗑 Cleared knowledge base and data directory")
        except Exception as e:
            logger.error(f"❌ Failed to clear knowledge base: {e}")
            raise PipelineError(f"Failed to clear knowledge base: {e}")


if __name__ == "__main__":
    config = AppConfig()
    crawler = CrawlerService(config)
    crawler.crawl_and_build_knowledge_base(max_pages=10)

    print("\n✅ Processed URLs:")
    for url in crawler.get_processed_urls():
        print(" -", url)
