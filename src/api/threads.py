from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from threads.store import ThreadsStore

router = APIRouter(prefix="/threads", tags=["threads"])


def get_threads(request: Request) -> ThreadsStore:
    return request.app.state.threads


Threads = Annotated[ThreadsStore, Depends(get_threads)]


class ThreadOut(BaseModel):
    thread_id: str
    title: str  # the first question of the chat
    updated_at: str


@router.get("/{user_id}")
def list_threads(user_id: str, threads: Threads) -> list[ThreadOut]:
    """The chats of one person, the most recently used first."""
    return [ThreadOut(**thread) for thread in threads.list(user_id)]
