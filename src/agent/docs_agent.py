# The docs worker: a small agent that can only use the official docs tool.

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.prompts import DOCS_WORKER_PROMPT


def build_docs_agent(llm: BaseChatModel, docs_tool: BaseTool) -> CompiledStateGraph:
    llm_with_tools = llm.bind_tools([docs_tool])

    def agent(state: MessagesState) -> dict:
        response = llm_with_tools.invoke([SystemMessage(DOCS_WORKER_PROMPT), *state["messages"]])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)  # pyrefly: ignore[bad-specialization]
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode([docs_tool], handle_tool_errors=True))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile()
