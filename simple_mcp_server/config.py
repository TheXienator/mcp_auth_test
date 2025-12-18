from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SECRET_KEY: str
    CLIENT_ID: str = "client_placeholder"
    CLIENT_SECRET: str = "placeholder"
    SERVER_URI: str = "http://localhost:8000"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    TEXT_STORAGE_PATH: str = "text_storage.txt"
    JOKE_STORAGE_PATH: str = "joke_storage.json"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
