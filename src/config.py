from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl, field_validator, model_validator
from pathlib import Path
from loguru import logger
import os
from typing import Optional, List
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class AppConfig(BaseSettings):
    # Core directories
    data_dir: str = Field(default=str(Path(__file__).resolve().parent.parent / "uploads"), description="Directory for storing uploaded documents")
    chroma_db_dir: str = Field(default=str(Path(__file__).resolve().parent.parent / "chroma_db"), description="Directory for ChromaDB storage")
    log_dir: str = Field(default=str(Path(__file__).resolve().parent.parent / "logs"), description="Directory for log files")
    
    # Website settings
    website_url: HttpUrl = Field(default="https://example.com", description="Website URL to crawl for RAG knowledge base")
    max_crawl_pages: int = Field(default=50, ge=1, le=500, description="Maximum number of pages to crawl")
    crawl_delay_min: float = Field(default=1.0, ge=0.5, le=5.0, description="Minimum delay between crawl requests in seconds")
    crawl_delay_max: float = Field(default=3.0, ge=1.0, le=10.0, description="Maximum delay between crawl requests in seconds")
    
    # Ollama settings
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama server URL")
    model_name: str = Field(default="llama3.1:latest", description="Ollama model name")
    
    # LLM parameters
    temperature: float = Field(default=0.4, ge=0.0, le=1.0, description="LLM temperature")
    max_tokens: int = Field(default=500, ge=100, le=2000, description="Maximum tokens for LLM response")
    
    # RAG parameters
    similarity_top_k: int = Field(default=3, ge=1, le=10, description="Number of similar documents to retrieve")
    chunk_size: int = Field(default=1024, description="Chunk size for text splitting")
    chunk_overlap: int = Field(default=128, description="Chunk overlap for text splitting")
    
    # Performance settings
    request_timeout: int = Field(default=60, ge=5, le=120, description="Request timeout in seconds")
    max_file_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum file size in MB")
    
    # Embedding model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace embedding model name"
    )
    
    # File processing
    supported_extensions: List[str] = Field(
        default=['.txt', '.md', '.pdf', '.docx', '.doc'],
        description="Supported file extensions"
    )
    
    # Logging
    log_level: str = Field(default="DEBUG", description="Logging level")
    log_rotation: str = Field(default="1 day", description="Log rotation schedule")
    log_retention: str = Field(default="7 days", description="Log retention period")
    
    # Security
    allowed_hosts: List[str] = Field(default=["*"], description="Allowed hosts for CORS")
    
    # Development settings
    debug: bool = Field(default=True, description="Enable debug mode")
    reload: bool = Field(default=True, description="Enable auto-reload")
    
    # API settings
    api_title: str = Field(default="HDB Financial Services Q&A System", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    api_description: str = Field(
        default="A RAG-based question answering system for HDB Financial Services loan information",
        description="API description"
    )
    
    # Voice settings
    voice_language: str = Field(default="en-US", description="Default language for STT and TTS")
    voice_name: str = Field(default="en-US-Wavenet-D", description="TTS voice name")
    voice_rate: float = Field(default=1.0, ge=0.5, le=2.0, description="TTS speaking rate")

    # Crawler settings
    user_agents: List[str] = Field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", 
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        ],
        description="List of user agents for rotation"
    )
    proxy_list: List[str] = Field(
        default_factory=lambda: [],
        description="List of proxy servers (e.g., http://proxy:port)"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

    @field_validator('user_agents', mode='before')
    @classmethod
    def parse_user_agents(cls, v):
        if isinstance(v, str):
            v = [agent.strip() for agent in v.split(',') if agent.strip()]
        if not v:
            raise ValueError("user_agents cannot be empty")
        return v

    @field_validator('proxy_list', mode='before')
    @classmethod
    def parse_proxy_list(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            proxies = [proxy.strip() for proxy in v.split(',') if proxy.strip()]
            return proxies
        return v

    @field_validator('data_dir', 'chroma_db_dir', 'log_dir')
    @classmethod
    def validate_directories(cls, v):
        path = Path(v)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise ValueError(f"Permission error while creating directory: {v}")
        return str(path)

    @field_validator('website_url')
    @classmethod
    def validate_website_url(cls, v):
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError("Website URL must start with http:// or https://")
        return url_str

    @field_validator('supported_extensions')
    @classmethod
    def validate_extensions(cls, v):
        return [ext if ext.startswith('.') else f'.{ext}' for ext in v]

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @model_validator(mode='after')
    def validate_chunk_overlap(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        return self

    @model_validator(mode='after')
    def validate_crawl_delay_max(self):
        if self.crawl_delay_max <= self.crawl_delay_min:
            raise ValueError("Maximum crawl delay must be greater than minimum crawl delay")
        return self

    def get_max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    def get_chunk_settings(self) -> dict:
        return {
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'length_function': len,
            'separators': ["\n\n", "\n", " ", ""]
        }

    def get_embedding_settings(self) -> dict:
        return {
            'model_name': self.embedding_model,
            'model_kwargs': {'device': 'cpu'},
            'encode_kwargs': {'normalize_embeddings': True}
        }

    def get_ollama_settings(self) -> dict:
        return {
            'model': self.model_name,
            'base_url': self.ollama_host,
            'timeout': self.request_timeout,
            'temperature': self.temperature
        }

    def get_voice_settings(self) -> dict:
        return {
            'language': self.voice_language,
            'voice_name': self.voice_name,
            'rate': self.voice_rate
        }

def setup_logging(config: AppConfig):
    try:
        import sys
        logger.remove()
        logger.add(
            sys.stderr,
            level=config.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
        log_file = Path(config.log_dir) / "rag_system.log"
        logger.add(
            log_file,
            level=config.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=config.log_rotation,
            retention=config.log_retention,
            compression="zip"
        )
        error_log_file = Path(config.log_dir) / "errors.log"
        logger.add(
            error_log_file,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=config.log_rotation,
            retention=config.log_retention,
            compression="zip"
        )
    except Exception as e:
        print(f"❌ Failed to setup logging: {e}")
        raise

def load_config(config_path: Optional[str] = None) -> AppConfig:
    try:
        config = AppConfig()
        logger.info(f"Loaded user_agents: {config.user_agents}")
        logger.info(f"Loaded proxy_list: {config.proxy_list}")
        setup_logging(config)
        logger.info(f"📁 Data directory: {config.data_dir}")
        logger.info(f"🗄️ ChromaDB directory: {config.chroma_db_dir}")
        logger.info(f"🌐 Website URL: {config.website_url}")
        logger.info(f"🤖 Ollama host: {config.ollama_host}")
        logger.info(f"📊 Model: {config.model_name}")
        logger.info(f"🔧 Temperature: {config.temperature}")
        logger.info(f"📄 Max tokens: {config.max_tokens}")
        logger.info(f"🔍 Similarity top-k: {config.similarity_top_k}")
        logger.info(f"📏 Chunk size: {config.chunk_size}")
        logger.info(f"📂 Supported extensions: {config.supported_extensions}")
        logger.info(f"🎙️ Voice language: {config.voice_language}")
        logger.info(f"🗣️ Voice name: {config.voice_name}")
        logger.info("✅ Configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        raise