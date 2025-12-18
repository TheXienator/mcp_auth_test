from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    MCP_SERVER_URI: str = "http://localhost:8000"
    ACCESS_TOKEN: str = ""  # Will be set dynamically
    ENABLE_DEBUG_LOGGING: bool = False

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
