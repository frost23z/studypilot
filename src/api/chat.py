from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field

router = APIRouter(prefix="/chat", tags=["chat"])


def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph


Graph = Annotated[CompiledStateGraph, Depends(get_graph)]


class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1, description="One conversation. Pick any text.")
    user_id: str = Field(
        min_length=1, description="Who is chatting. Long-term memory is kept per user_id."
    )
    message: str = Field(min_length=1)


class ApproveRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    approved: bool = Field(description="true saves the note, false saves nothing")


class PendingNote(BaseModel):
    title: str
    content: str


class ChatResponse(BaseModel):
    thread_id: str
    reply: str | None  # the answer, or None while a note waits for approval
    pending_note: PendingNote | None


def make_config(thread_id: str) -> RunnableConfig:
    # recursion_limit stops the supervisor loop if it never settles on an answer.
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 12}


async def is_waiting_for_approval(graph: CompiledStateGraph, config: RunnableConfig) -> bool:
    state = await graph.aget_state(config)
    return any(task.interrupts for task in state.tasks)


async def run(graph: CompiledStateGraph, graph_input, thread_id: str) -> ChatResponse:
    result = await graph.ainvoke(graph_input, make_config(thread_id))
    if "__interrupt__" in result:
        draft = result["__interrupt__"][0].value
        return ChatResponse(thread_id=thread_id, reply=None, pending_note=PendingNote(**draft))
    return ChatResponse(thread_id=thread_id, reply=result["messages"][-1].text, pending_note=None)


@router.post("")
async def chat(body: ChatRequest, graph: Graph) -> ChatResponse:
    if await is_waiting_for_approval(graph, make_config(body.thread_id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A note is waiting for approval. Answer it with POST /chat/approve first.",
        )
    graph_input = {"messages": [HumanMessage(body.message)], "user_id": body.user_id}
    return await run(graph, graph_input, body.thread_id)


@router.post("/approve")
async def approve(body: ApproveRequest, graph: Graph) -> ChatResponse:
    if not await is_waiting_for_approval(graph, make_config(body.thread_id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Nothing is waiting for approval in this thread."
        )
    return await run(graph, Command(resume=body.approved), body.thread_id)
