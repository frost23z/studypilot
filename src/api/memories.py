from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langgraph.store.base import BaseStore
from pydantic import BaseModel

from memory.facts import delete_fact, list_facts

router = APIRouter(prefix="/memories", tags=["memories"])


def get_memory(request: Request) -> BaseStore:
    return request.app.state.memory


Memory = Annotated[BaseStore, Depends(get_memory)]


class FactOut(BaseModel):
    id: str
    text: str


@router.get("/{user_id}")
async def get_facts(user_id: str, memory: Memory) -> list[FactOut]:
    return [FactOut(**fact) for fact in await list_facts(memory, user_id)]


@router.delete("/{user_id}/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_fact(user_id: str, fact_id: str, memory: Memory) -> None:
    if not await delete_fact(memory, user_id, fact_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fact not found.")
