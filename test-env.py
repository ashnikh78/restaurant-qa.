from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
import os

class AppConfig(BaseSettings):
    # Crawler settings
    user_agents: List[str] = Field(
        description="List of user agents for rotation"
    )
    proxy_list: List[str] = Field(
        default=["http://proxy1.com", "http://proxy2.com"], description="List of proxy servers"
    )

    model_config = {
        "env_file": ".env",  # Ensure this is the correct path for your .env
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

    # Custom field_validator to manually parse the user_agents
    @field_validator('user_agents', mode='before')
    @classmethod
    def parse_user_agents(cls, v):
        """Manually parse the user_agents from a comma-separated string or return as-is if already a list"""
        if isinstance(v, str):
            v = [agent.strip() for agent in v.split(',') if agent.strip()]
        if not v:
            raise ValueError("user_agents cannot be empty")
        return v

    @field_validator('proxy_list', mode='before')
    @classmethod
    def parse_proxy_list(cls, v):
        """Parse proxy_list from comma-separated string or return as-is if already a list"""
        if isinstance(v, str):
            v = [proxy.strip() for proxy in v.split(',') if proxy.strip()]
        return v

# Check if the environment variables are loaded correctly
print(f"USER_AGENTS from .env: {os.getenv('USER_AGENTS')}")
print(f"PROXY_LIST from .env: {os.getenv('PROXY_LIST')}")

# Load the config and print values
try:
    config = AppConfig()
    print(f"USER_AGENTS: {config.user_agents}")
    print(f"PROXY_LIST: {config.proxy_list}")
except Exception as e:
    print(f"Error loading config: {e}")
