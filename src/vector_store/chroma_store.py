from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from core.config import get_settings


def get_vector_store(embedding: Embeddings) -> Chroma:
    return Chroma(
        collection_name=get_settings().CHROMA_COLLECTION_NAME,
        embedding_function=embedding,
        persist_directory=get_settings().CHROMA_PERSIST_DIRECTORY,
        collection_configuration={"hnsw": {"space": "cosine"}},
    )
