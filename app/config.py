from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings, env_file=".env", extra="ignore"):
    database_url: str


# Lazy, so importing the app (e.g. in tests) needs no DATABASE_URL.
@lru_cache
def get_settings() -> Settings:
    return Settings()
