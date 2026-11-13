import os
import sys
from pathlib import Path

from fastmcp.client.transports import StdioTransport
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from agent.docs_agent import build_docs_agent
from agent.prompts import COURSE_WORKER_PROMPT
from agent.rag import build_graph
from agent.supervisor import build_supervisor
from agent.tools import make_docs_tool
from core.config import get_settings
from embedding.gemini_embedding import get_embeddings
from ingestion.manifest import IngestionManifest
from notes.client import make_save_note
from vector_store.chroma_store import get_vector_store

settings = get_settings()
if not settings.GOOGLE_API_KEYS:
    message = "Set GOOGLE_API_KEYS in .env"
    raise RuntimeError(message)

if not settings.TAVILY_API_KEY:
    message = "Set TAVILY_API_KEY in .env"
    raise RuntimeError(message)

api_key = settings.GOOGLE_API_KEYS[settings.CURRENT_GOOGLE_API_KEY]
manifest = IngestionManifest(Path(settings.CHROMA_PERSIST_DIRECTORY) / "manifest.sqlite3")
tavily = TavilySearch(
    tavily_api_key=settings.TAVILY_API_KEY.get_secret_value(),
    max_results=settings.TAVILY_MAX_RESULTS,
)

notes_server = StdioTransport(
    command=sys.executable,
    args=["-m", "notes"],
    env=dict(os.environ),
    keep_alive=False,
)
save_note = make_save_note(notes_server)


def create_graph(checkpointer: BaseCheckpointSaver | None = None, store: BaseStore | None = None):
    llm = ChatGoogleGenerativeAI(model=settings.GOOGLE_CHAT_MODEL, api_key=api_key)

    course_worker = build_graph(
        vector_store=get_vector_store(get_embeddings(api_key)),
        llm=llm,
        top_k=settings.RETRIEVAL_TOP_K,
        max_rewrites=settings.MAX_QUERY_REWRITES,
        search_filter=manifest.active_filter,
        system_prompt=COURSE_WORKER_PROMPT,
    )

    docs_worker = build_docs_agent(llm, make_docs_tool(tavily))

    return build_supervisor(
        llm,
        course_worker,
        docs_worker,
        save_note,
        checkpointer=checkpointer,
        store=store,
        summary_after=settings.SUMMARY_AFTER_MESSAGES,
        keep_messages=settings.SUMMARY_KEEP_MESSAGES,
    )


graph = create_graph()
