from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from agent.prompts import ANSWER_PROMPT, NO_RESULTS, SUPERVISOR_PROMPT

NextStep = Literal["course_worker", "docs_worker", "answer"]


class State(MessagesState):
    next_step: str
    course_notes: str  # course worker's latest findings
    docs_notes: str  # docs worker's latest findings


class Route(BaseModel):
    next_step: NextStep = Field(description="Who works next")


def build_supervisor(
    llm: BaseChatModel,
    course_worker: Runnable,
    docs_worker: Runnable,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    router = llm.with_structured_output(Route)

    def supervisor(state: State) -> dict:
        status = (
            f"- course worker: {'done' if state.get('course_notes') else 'not done yet'}\n"
            f"- docs worker: {'done' if state.get('docs_notes') else 'not done yet'}"
        )
        route = Route.model_validate(
            router.invoke(
                [SystemMessage(SUPERVISOR_PROMPT.format(status=status)), *state["messages"]]
            )
        )
        next_step = route.next_step
        # a worker never runs twice for the same question
        if next_step == "course_worker" and state.get("course_notes"):
            next_step = "answer"
        if next_step == "docs_worker" and state.get("docs_notes"):
            next_step = "answer"
        return {"next_step": next_step}

    # only the final text of a worker is kept
    def course_node(state: State) -> dict:
        result = course_worker.invoke({"messages": state["messages"]})
        return {"course_notes": result["messages"][-1].text or NO_RESULTS}

    def docs_node(state: State) -> dict:
        result = docs_worker.invoke({"messages": state["messages"]})
        return {"docs_notes": result["messages"][-1].text or NO_RESULTS}

    def answer(state: State) -> dict:
        prompt = ANSWER_PROMPT.format(
            course_notes=state.get("course_notes") or "(not searched)",
            docs_notes=state.get("docs_notes") or "(not searched)",
        )
        response = llm.invoke([SystemMessage(prompt), *state["messages"]])
        # clear the worker results for the next question
        return {"messages": [response], "course_notes": "", "docs_notes": ""}

    def pick_worker(state: State) -> NextStep:
        return state["next_step"]  # pyrefly: ignore[bad-return]

    builder = StateGraph(State)  # pyrefly: ignore[bad-specialization]
    builder.add_node("supervisor", supervisor)
    builder.add_node("course_worker", course_node)
    builder.add_node("docs_worker", docs_node)
    builder.add_node("answer", answer)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", pick_worker)
    builder.add_edge("course_worker", "supervisor")
    builder.add_edge("docs_worker", "supervisor")
    builder.add_edge("answer", END)

    return builder.compile(checkpointer=checkpointer)
