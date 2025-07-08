from pydantic_settings import BaseSettings
from pathlib import Path
import yaml

class AppConfig(BaseSettings):
    llm_model: str = "deepseek-llm:7b"
    embed_model: str = "all-MiniLM-L6-v2"
    data_dir: Path = Path("./data")
    chroma_persist_dir: Path = Path("./chroma_db")
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retriever_k: int = 3
    llm_temperature: float = 0.7

    class Config:
        env_prefix = "APP_"

def load_config(config_path: str = "config.yaml") -> AppConfig:
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    return AppConfig(**config_data)