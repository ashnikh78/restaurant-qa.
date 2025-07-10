from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader, TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.embeddings import HuggingFaceEmbeddings
from loguru import logger
from pathlib import Path
from typing import List, Tuple, Optional
import asyncio
import os
import sys
import datetime
import requests

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.async_api import async_playwright, Browser

class PipelineError(Exception):
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(self.message)

class RAGPipeline:
    def __init__(self, config: 'AppConfig'):
        self.config = config
        self.llm = None
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        self.documents_dir = Path(config.data_dir)
        self.browser: Optional[Browser] = None
        self.initialization_status = "not_initialized"

    async def initialize_async(self):
        try:
            logger.info("Initializing RAG pipeline...")
            # Check Ollama connectivity
            try:
                logger.debug(f"Checking Ollama connectivity at {self.config.ollama_host}")
                response = requests.get(f"{self.config.ollama_host}/api/tags")
                if response.status_code != 200:
                    raise Exception(f"Ollama server returned {response.status_code}")
                models = response.json().get('models', [])
                if not any(model['name'] == self.config.model_name for model in models):
                    raise Exception(f"Model {self.config.model_name} not found")
                logger.debug(f"Ollama server available, model {self.config.model_name} found")
            except Exception as e:
                logger.error(f"Ollama connectivity check failed: {e}")
                self.initialization_status = f"failed_ollama: {str(e)}"
                raise PipelineError(f"Ollama connectivity check failed: {e}")

            # Initialize LLM
            try:
                logger.debug(f"Initializing ChatOllama with model {self.config.model_name}")
                self.llm = ChatOllama(**self.config.get_ollama_settings())
                # Test LLM with a simple query
                test_response = await self.llm.ainvoke("ping")
                if not test_response:
                    raise Exception("LLM ping returned empty response")
                logger.info("ChatOllama initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ChatOllama: {e}")
                self.initialization_status = f"failed_llm: {str(e)}"
                raise PipelineError(f"ChatOllama initialization failed: {e}")

            # Initialize vector store
            try:
                logger.debug(f"Initializing Chroma vector store at {self.config.chroma_db_dir}")
                self.vectorstore = Chroma(
                    collection_name="hdb_financial_qa",
                    embedding_function=HuggingFaceEmbeddings(**self.config.get_embedding_settings()),
                    persist_directory=self.config.chroma_db_dir
                )
                # Test vectorstore and log state
                vectorstore_data = self.vectorstore.get()
                logger.debug(f"Vectorstore initialized, document count: {len(vectorstore_data['ids'])}")
                if not vectorstore_data['ids']:
                    logger.warning("Vectorstore is empty; no documents indexed")
                self.vectorstore.get()
                logger.info("Chroma vector store initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Chroma: {e}")
                self.initialization_status = f"failed_chroma: {str(e)}"
                raise PipelineError(f"Chroma initialization failed: {e}")

            # Initialize Playwright browser
            try:
                async with async_playwright() as p:
                    try:
                        logger.debug("Launching Playwright Chromium browser")
                        self.browser = await p.chromium.launch(headless=True)
                        logger.info("Playwright browser initialized successfully")
                    except NotImplementedError as e:
                        logger.warning(f"NotImplementedError in Playwright browser initialization: {e}")
                        self.browser = None
                    except Exception as e:
                        logger.warning(f"Failed to initialize Playwright browser: {e}")
                        self.browser = None
            except Exception as e:
                logger.warning(f"Playwright initialization failed: {e}")
                self.browser = None

            # Crawl website
            try:
                logger.debug(f"Crawling website: {self.config.website_url}")
                await self._crawl_websites()
            except Exception as e:
                logger.warning(f"Web crawling skipped due to error: {e}")

            # Process existing documents
            logger.debug(f"Processing existing documents in {self.documents_dir}")
            await self._process_existing_documents()
            self.initialization_status = "success"
            logger.info("RAG pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Pipeline initialization failed: {e}")
            self.initialization_status = f"failed_general: {str(e)}"
            raise PipelineError(f"Async initialization failed: {e}")

    async def _crawl_websites(self):
        if not self.browser:
            logger.warning("No browser available for crawling")
            return

        documents = []
        url = self.config.website_url
        try:
            logger.info(f"Crawling {url}")
            loader = WebBaseLoader(url)
            docs = loader.load()
            documents.extend(docs)
            logger.info(f"Successfully crawled {url}")
        except Exception as e:
            logger.error(f"Failed to crawl {url}: {e}")
            return

        if documents:
            splits = self.text_splitter.split_documents(documents)
            self.vectorstore.add_documents(splits)
            logger.info(f"Added {len(splits)} document splits from website")

    async def _process_existing_documents(self):
        self.documents_dir.mkdir(exist_ok=True)
        for file_path in self.documents_dir.glob("*"):
            if file_path.is_file():
                try:
                    await self._process_file(file_path)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")

    async def _process_file(self, file_path: Path):
        try:
            if file_path.suffix not in self.config.supported_extensions:
                logger.warning(f"Unsupported file type: {file_path}")
                return
            if file_path.suffix == ".txt" or file_path.suffix == ".md":
                loader = TextLoader(str(file_path))
            elif file_path.suffix == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif file_path.suffix in [".doc", ".docx"]:
                loader = Docx2txtLoader(str(file_path))
            else:
                return

            documents = loader.load()
            splits = self.text_splitter.split_documents(documents)
            self.vectorstore.add_documents(splits)
            logger.info(f"Processed and added {file_path.name}")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    async def process_voice_query(self, query: str, customer_data: str = "") -> Tuple[str, List[str]]:
        try:
            logger.debug(f"Processing query: {query}, customer_data: {customer_data}")
            if not self.vectorstore:
                logger.error("Vectorstore is None")
                raise PipelineError("Vectorstore not initialized", code=503)
            if not self.llm:
                logger.error("LLM is None")
                raise PipelineError("LLM not initialized", code=503)
            prompt_template = (
                "Context: {context}\n"
                "Customer Data: {customer_data}\n"
                "Question: {question}\n"
                "Answer:"
            )
            prompt = ChatPromptTemplate.from_template(prompt_template)
            logger.debug(f"Performing similarity search with top_k={self.config.similarity_top_k}")
            try:
                docs = self.vectorstore.similarity_search(query, k=self.config.similarity_top_k)
            except Exception as e:
                logger.error(f"Similarity search failed: {e}")
                raise PipelineError(f"Similarity search failed: {e}", code=500)
            context = "\n".join([doc.page_content for doc in docs])
            sources = [doc.metadata.get("source", "Unknown") for doc in docs]
            logger.debug(f"Retrieved {len(docs)} documents, sources: {sources}")
            chain = prompt | self.llm
            try:
                response = await chain.ainvoke({"context": context, "question": query, "customer_data": customer_data})
            except Exception as e:
                logger.error(f"LLM invocation failed: {e}")
                raise PipelineError(f"LLM invocation failed: {e}", code=500)
            logger.debug(f"Query response: {response.content[:50]}...")
            return response.content, sources
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise PipelineError(f"Query processing failed: {e}", code=500)

    def add_documents(self, file_paths: List[Path]):
        for file_path in file_paths:
            try:
                asyncio.run(self._process_file(file_path))
            except Exception as e:
                logger.error(f"Failed to add document {file_path}: {e}")
                raise PipelineError(f"Failed to add document {file_path}: {e}")

    def list_documents(self) -> List[dict]:
        try:
            documents = []
            for file_path in self.documents_dir.glob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    last_modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    documents.append({
                        "filename": file_path.name,
                        "size_kb": round(stat.st_size / 1024, 2),
                        "last_modified": last_modified
                    })
            logger.debug(f"Listed documents: {documents}")
            return documents
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise PipelineError(f"Failed to list documents: {e}")

    def delete_document(self, filename: str) -> dict:
        try:
            file_path = self.documents_dir / filename
            if not file_path.exists():
                logger.error(f"File {filename} not found")
                raise PipelineError(f"File {filename} not found", code=404)
            file_path.unlink()
            logger.info(f"Deleted {filename}")
            return {"message": f"Deleted {filename} successfully"}
        except Exception as e:
            logger.error(f"Failed to delete {filename}: {e}")
            raise PipelineError(f"Failed to delete {filename}: {e}")

    def get_stats(self) -> dict:
        try:
            stats = {
                "total_documents": len(list(self.documents_dir.glob("*"))),
                "vectorstore_size": len(self.vectorstore.get()["ids"]) if self.vectorstore else 0
            }
            logger.debug(f"Stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise PipelineError(f"Failed to get stats: {e}")

    def health_check(self) -> bool:
        try:
            if self.llm is None:
                logger.error(f"Health check failed: LLM is None, initialization_status={self.initialization_status}")
                return False
            if self.vectorstore is None:
                logger.error(f"Health check failed: Vectorstore is None, initialization_status={self.initialization_status}")
                return False
            try:
                # Test LLM connectivity
                response = self.llm.invoke("ping")
                if not response:
                    logger.error(f"Health check failed: LLM ping failed, initialization_status={self.initialization_status}")
                    return False
            except Exception as e:
                logger.error(f"Health check failed: LLM ping error: {e}, initialization_status={self.initialization_status}")
                return False
            try:
                # Test vectorstore
                vectorstore_data = self.vectorstore.get()
                logger.debug(f"Health check: Vectorstore document count: {len(vectorstore_data['ids'])}")
                if not vectorstore_data['ids']:
                    logger.warning("Health check: Vectorstore is empty")
            except Exception as e:
                logger.error(f"Health check failed: Vectorstore error: {e}, initialization_status={self.initialization_status}")
                return False
            logger.debug(f"Health check passed: LLM and Vectorstore are initialized, initialization_status={self.initialization_status}")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}, initialization_status={self.initialization_status}")
            return False

    def __del__(self):
        if self.browser:
            asyncio.run(self.browser.close())
            logger.info("Playwright browser closed")