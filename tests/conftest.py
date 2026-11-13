from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from api.main import create_app
from core.config import get_settings


class FakeGraph:
    """A stand-in for the agent, so the API can be tested without any API keys.

    It remembers the messages of each thread and answers with a fixed reply.
    """

    def __init__(self, reply: str = "Hello!") -> None:
        self.reply = reply
        self.threads: dict[str, list] = {}

    async def ainvoke(self, graph_input, config) -> dict:
        thread = self.threads.setdefault(config["configurable"]["thread_id"], [])
        thread.extend([*graph_input["messages"], AIMessage(self.reply)])
        return {"messages": thread}

    async def aget_state(self, config) -> SimpleNamespace:
        thread = self.threads.get(config["configurable"]["thread_id"], [])
        return SimpleNamespace(values={"messages": thread}, tasks=[])


@pytest.fixture
def documents(tmp_path: Path) -> Path:
    folder = tmp_path / "documents"
    folder.mkdir()
    return folder


@pytest.fixture
def graph() -> FakeGraph:
    return FakeGraph()


@pytest.fixture
def client(
    tmp_path: Path, documents: Path, graph: FakeGraph, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """The real API on temporary databases, with a fake agent."""
    monkeypatch.setenv("TAVILY_API_KEY", "test")
    monkeypatch.setenv("NOTES_DB_PATH", str(tmp_path / "notes.sqlite3"))
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(tmp_path / "chat_memory.sqlite3"))
    monkeypatch.setenv("MEMORY_DB_PATH", str(tmp_path / "long_term_memory.sqlite3"))
    monkeypatch.setenv("THREADS_DB_PATH", str(tmp_path / "threads.sqlite3"))
    monkeypatch.setenv("DOCUMENTS_DIR", str(documents))
    get_settings.cache_clear()
    with TestClient(create_app(make_graph=lambda _saver, _memory: graph)) as test_client:
        yield test_client
    get_settings.cache_clear()
