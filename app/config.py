from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"

@lru_cache()  # ← Скобки обязательны
def get_settings() -> Settings:
    return Settings()
