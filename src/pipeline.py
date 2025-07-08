from typing import Tuple
from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.chains import RetrievalQAWithSourcesChain
from loguru import logger
from pathlib import Path
from .config import AppConfig

class PipelineError(Exception):
    """Custom exception for pipeline errors."""
    pass

class RAGPipeline:
    def __init__(self, config: AppConfig):
        logger.info("Initializing RAG pipeline...")
        self.config = config
        try:
            self.llm = Ollama(model=config.llm_model, temperature=config.llm_temperature)
            self.embeddings = HuggingFaceEmbeddings(model_name=config.embed_model)
            self.vector_store = self._init_vector_store()
            self.qa_chain = self._init_qa_chain()
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise PipelineError(f"Initialization failed: {e}")

    def _init_vector_store(self) -> Chroma:
        try:
            documents = []
            for file_path in self.config.data_dir.glob("*.txt"):
                loader = TextLoader(str(file_path), encoding="utf-8")
                raw_docs = loader.load()
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap
                )
                documents.extend(splitter.split_documents(raw_docs))
            
            if not documents:
                logger.error("No documents loaded.")
                raise PipelineError("No documents loaded.")
            
            logger.info(f"Loaded and split {len(documents)} document chunks.")
            
            return Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=str(self.config.chroma_persist_dir)
            )
        except Exception as e:
            logger.error(f"Vector store initialization failed: {e}")
            raise PipelineError(f"Vector store initialization failed: {e}")

    def _init_qa_chain(self) -> RetrievalQAWithSourcesChain:
        try:
            retriever = self.vector_store.as_retriever(search_kwargs={"k": self.config.retriever_k})
            return RetrievalQAWithSourcesChain.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                verbose=False
            )
        except Exception as e:
            logger.error(f"QA chain initialization failed: {e}")
            raise PipelineError(f"QA chain initialization failed: {e}")

    def answer_query(self, query: str) -> Tuple[str, str]:
        if not query.strip():
            logger.warning("Empty query received.")
            return "Please enter a question.", ""
        
        logger.info(f"Processing query: {query}")
        try:
            result = self.qa_chain.invoke({"question": query})
            answer = result.get("answer", "No answer found.")
            sources = result.get("sources", "No sources identified.")
            logger.info(f"Answer generated: {answer[:100]}...")
            return answer.strip(), sources
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise PipelineError(f"Query processing failed: {e}")