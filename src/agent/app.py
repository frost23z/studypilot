from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.rag import build_graph
from core.config import get_settings
from embedding.gemini_embedding import get_embeddings
from ingestion.manifest import IngestionManifest
from vector_store.chroma_store import get_vector_store

settings = get_settings()
if not settings.GOOGLE_API_KEYS:
    message = "Set GOOGLE_API_KEYS in .env"
    raise RuntimeError(message)

api_key = settings.GOOGLE_API_KEYS[settings.CURRENT_GOOGLE_API_KEY]
manifest = IngestionManifest(Path(settings.CHROMA_PERSIST_DIRECTORY) / "manifest.sqlite3")


def create_graph(checkpointer: BaseCheckpointSaver | None = None):
    return build_graph(
        vector_store=get_vector_store(get_embeddings(api_key)),
        llm=ChatGoogleGenerativeAI(model=settings.GOOGLE_CHAT_MODEL, api_key=api_key),
        top_k=settings.RETRIEVAL_TOP_K,
        max_rewrites=settings.MAX_QUERY_REWRITES,
        search_filter=manifest.active_filter,
        checkpointer=checkpointer,
    )


graph = create_graph()
