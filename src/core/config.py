# https://aistudio.google.com/docs/models
# https://aistudio.google.com/docs/embeddings#quality-for-smaller-dimensions

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "studypilot"
    debug: bool = False

    GOOGLE_API_KEYS: list[SecretStr] = Field(
        default_factory=list,
        description="Google API keys for rotation.",
    )
    CURRENT_GOOGLE_API_KEY: int = 0
    GOOGLE_CHAT_MODEL: str = "gemini-3.5-flash-lite"
    GOOGLE_EMBEDDING_MODEL: str = "gemini-embedding-001"
    # Have to manually normalize for non-3072 dimension with gemini-embedding-001 model
    EMBEDDING_DIMENSION: int = 3072
    EMBEDDING_BATCH_SIZE: int = 100

    RETRIEVAL_TOP_K: int = 4
    MAX_QUERY_REWRITES: int = 2

    TAVILY_API_KEY: SecretStr
    TAVILY_MAX_RESULTS: int = 3

    CHROMA_COLLECTION_NAME: str = "course_materials"
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_langchain_db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
