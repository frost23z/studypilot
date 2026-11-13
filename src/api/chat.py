from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field

from api.documents import Documents
from api.sources import Source, find_sources
from api.threads import Threads

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
    sources: list[Source] = []  # the course files the answer cites
    pending_note: PendingNote | None


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    sources: list[Source] = []  # the course files an answer cites


class HistoryResponse(BaseModel):
    thread_id: str
    messages: list[HistoryMessage]  # old messages are gone once a long chat was summarized
    pending_note: PendingNote | None  # set while a note waits for approval


def make_config(thread_id: str) -> RunnableConfig:
    # recursion_limit stops the supervisor loop if it never settles on an answer.
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 12}


async def is_waiting_for_approval(graph: CompiledStateGraph, config: RunnableConfig) -> bool:
    state = await graph.aget_state(config)
    return any(task.interrupts for task in state.tasks)


async def run(
    graph: CompiledStateGraph, graph_input, thread_id: str, documents: Path
) -> ChatResponse:
    result = await graph.ainvoke(graph_input, make_config(thread_id))
    if "__interrupt__" in result:
        draft = result["__interrupt__"][0].value
        return ChatResponse(thread_id=thread_id, reply=None, pending_note=PendingNote(**draft))
    reply = result["messages"][-1].text
    sources = find_sources(reply, documents)
    return ChatResponse(thread_id=thread_id, reply=reply, sources=sources, pending_note=None)


@router.get("/{thread_id}")
async def history(thread_id: str, graph: Graph, documents: Documents) -> HistoryResponse:
    """What the chat shows: the saved messages of one thread. Empty for a new thread."""
    state = await graph.aget_state(make_config(thread_id))
    messages = []
    for message in state.values.get("messages", []):
        if isinstance(message, HumanMessage) and message.text:
            messages.append(HistoryMessage(role="user", text=message.text))
        elif isinstance(message, AIMessage) and message.text:
            sources = find_sources(message.text, documents)
            messages.append(HistoryMessage(role="assistant", text=message.text, sources=sources))
    draft = next((task.interrupts[0].value for task in state.tasks if task.interrupts), None)
    pending_note = PendingNote(**draft) if draft else None
    return HistoryResponse(thread_id=thread_id, messages=messages, pending_note=pending_note)


@router.post("")
async def chat(
    body: ChatRequest, graph: Graph, threads: Threads, documents: Documents
) -> ChatResponse:
    if await is_waiting_for_approval(graph, make_config(body.thread_id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A note is waiting for approval. Answer it with POST /chat/approve first.",
        )
    graph_input = {"messages": [HumanMessage(body.message)], "user_id": body.user_id}
    response = await run(graph, graph_input, body.thread_id, documents)
    threads.touch(body.thread_id, body.user_id, body.message)  # lists the chat for its owner
    return response


@router.post("/approve")
async def approve(
    body: ApproveRequest, graph: Graph, threads: Threads, documents: Documents
) -> ChatResponse:
    if not await is_waiting_for_approval(graph, make_config(body.thread_id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Nothing is waiting for approval in this thread."
        )
    response = await run(graph, Command(resume=body.approved), body.thread_id, documents)
    threads.bump(body.thread_id)
    return response
