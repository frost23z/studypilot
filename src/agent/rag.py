# https://docs.langchain.com/oss/python/langgraph/graph-api
# https://docs.langchain.com/oss/python/langgraph/agentic-rag

from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.vectorstores import VectorStore
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.prompts import SYSTEM_PROMPT
from agent.tools import make_retrieve_tool


def build_graph(
    vector_store: VectorStore,
    llm: BaseChatModel,
    *,
    top_k: int = 4,
    search_filter: Callable[[], dict | None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    tools = [make_retrieve_tool(vector_store, top_k, search_filter)]
    llm_with_tools = llm.bind_tools(tools)

    def agent(state: MessagesState) -> dict:
        response = llm_with_tools.invoke([SystemMessage(SYSTEM_PROMPT), *state["messages"]])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)  # pyrefly: ignore[bad-specialization]
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer)
