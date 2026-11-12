# https://docs.langchain.com/oss/python/langgraph/graph-api
# https://docs.langchain.com/oss/python/langgraph/agentic-rag

from collections.abc import Callable
from typing import Literal
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langchain_core.vectorstores import VectorStore
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from agent.prompts import GRADE_PROMPT, REWRITE_PROMPT, SYSTEM_PROMPT
from agent.tools import make_retrieve_tool


class State(MessagesState):
    rewrites: int


class Grade(BaseModel):
    relevant: bool = Field(description="True if the passages help answer the question")


def last_question(messages: list[AnyMessage]) -> str:
    """The latest thing the intern typed."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.text
    return ""


def latest_tool_results(messages: list[AnyMessage]) -> list[ToolMessage]:
    """The tool results added since the model last spoke."""
    results = []
    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            break
        results.append(message)
    return results


def build_graph(
    vector_store: VectorStore,
    llm: BaseChatModel,
    *,
    top_k: int = 4,
    max_rewrites: int = 2,
    search_filter: Callable[[], dict | None] | None = None,
    docs_tool: BaseTool | None = None,
    system_prompt: str = SYSTEM_PROMPT,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    retrieve = make_retrieve_tool(vector_store, top_k, search_filter)
    tools = [retrieve, docs_tool] if docs_tool else [retrieve]
    llm_with_tools = llm.bind_tools(tools)
    grader = llm.with_structured_output(Grade)

    def agent(state: State) -> dict:
        response = llm_with_tools.invoke([SystemMessage(system_prompt), *state["messages"]])
        return {"messages": [response], "rewrites": 0}

    def grade_documents(state: State) -> Literal["agent", "rewrite"]:
        # Only the course search is graded. Official docs results go straight to the model.
        course_results = [
            m for m in latest_tool_results(state["messages"]) if m.name == retrieve.name
        ]
        if not course_results or state.get("rewrites", 0) >= max_rewrites:
            return "agent"  # nothing to grade, or tried enough already
        passages = course_results[0].text
        prompt = GRADE_PROMPT.format(question=last_question(state["messages"]), passages=passages)
        grade = Grade.model_validate(grader.invoke([HumanMessage(prompt)]))
        return "agent" if grade.relevant else "rewrite"

    def rewrite(state: State) -> dict:
        question = last_question(state["messages"])
        new_query = llm.invoke([HumanMessage(REWRITE_PROMPT.format(question=question))]).text
        tool_call = {"name": retrieve.name, "args": {"query": new_query}, "id": str(uuid4())}
        return {
            "messages": [AIMessage("", tool_calls=[tool_call])],
            "rewrites": state.get("rewrites", 0) + 1,
        }

    builder = StateGraph(State)  # pyrefly: ignore[bad-specialization]
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    builder.add_node("rewrite", rewrite)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_conditional_edges("tools", grade_documents)
    builder.add_edge("rewrite", "tools")

    return builder.compile(checkpointer=checkpointer)
