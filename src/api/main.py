"""StudyPilot API.

doppler run -- uv run uvicorn api.main:app --reload
"""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.base import BaseStore
from langgraph.store.sqlite.aio import AsyncSqliteStore

from api import chat, documents, memories, notes, threads
from core.config import get_settings
from notes.store import NotesStore
from threads.store import ThreadsStore


def create_app(
    make_graph: Callable[[BaseCheckpointSaver, BaseStore], object] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        settings = get_settings()
        app.state.store = NotesStore(settings.NOTES_DB_PATH)
        app.state.threads = ThreadsStore(settings.THREADS_DB_PATH)
        app.state.documents = Path(settings.DOCUMENTS_DIR)
        # Chat memory (one thread) and long-term memory (across threads) are separate files.
        async with (
            AsyncSqliteSaver.from_conn_string(settings.CHECKPOINT_DB_PATH) as saver,
            AsyncSqliteStore.from_conn_string(settings.MEMORY_DB_PATH) as memory,
        ):
            await memory.setup()
            app.state.memory = memory
            if make_graph is None:
                # imported here because agent.app needs the API keys
                from agent.app import create_graph

                app.state.graph = create_graph(checkpointer=saver, store=memory)
            else:
                app.state.graph = make_graph(saver, memory)
            yield

    app = FastAPI(title="StudyPilot", lifespan=lifespan)
    app.include_router(notes.router)
    app.include_router(chat.router)
    app.include_router(memories.router)
    app.include_router(threads.router)
    app.include_router(documents.router)
    return app


app = create_app()
