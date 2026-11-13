from collections.abc import Awaitable, Callable
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, RemoveMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from agent.prompts import (
    ANSWER_PROMPT,
    MEMORY_PROMPT,
    NO_RESULTS,
    NOTES_WORKER_PROMPT,
    SUMMARY_NOTE,
    SUMMARY_PROMPT,
    SUPERVISOR_PROMPT,
)
from memory.facts import add_facts, list_facts

NextStep = Literal["course_worker", "docs_worker", "notes_worker", "answer"]


class State(MessagesState):
    user_id: str
    summary: str  # summary of the older messages that were removed from the chat
    next_step: str
    course_notes: str  # course worker's latest findings
    docs_notes: str  # docs worker's latest findings
    note_draft: dict  # the note the intern is asked to approve: title and content
    note_result: str  # what happened to the note: saved, declined or failed


class Note(BaseModel):
    title: str = Field(description="Short title, a few words")
    content: str = Field(description="The note: 3 to 8 short plain lines")


class Facts(BaseModel):
    facts: list[str] = Field(description="New short facts about the intern, or an empty list")


class Route(BaseModel):
    next_step: NextStep = Field(description="Who works next")


def build_supervisor(
    llm: BaseChatModel,
    course_worker: Runnable,
    docs_worker: Runnable,
    save_note: Callable[[str, str], Awaitable[str]],
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
    summary_after: int = 10,
    keep_messages: int = 4,
) -> CompiledStateGraph:
    router = llm.with_structured_output(Route)
    note_writer = llm.with_structured_output(Note)
    fact_finder = llm.with_structured_output(Facts)

    def history(state: State) -> list[AnyMessage]:
        if state.get("summary"):
            return [
                SystemMessage(SUMMARY_NOTE.format(summary=state["summary"])),
                *state["messages"],
            ]
        return state["messages"]

    def needs_summary(state: State) -> Literal["summarize", "supervisor"]:
        return "summarize" if len(state["messages"]) > summary_after else "supervisor"

    async def summarize(state: State) -> dict:
        messages = state["messages"]
        # Keep the last few messages, and start the kept part at an intern message.
        cut = len(messages) - keep_messages
        while cut < len(messages) and not isinstance(messages[cut], HumanMessage):
            cut += 1
        old = messages[:cut]
        if not old:
            return {}
        conversation = "\n".join(
            f"{'Intern' if isinstance(m, HumanMessage) else 'StudyPilot'}: {m.text}" for m in old
        )
        prompt = SUMMARY_PROMPT.format(
            summary=state.get("summary") or "(none yet)", conversation=conversation
        )
        response = await llm.ainvoke([HumanMessage(prompt)])
        return {
            "summary": response.text,
            "messages": [RemoveMessage(id=m.id) for m in old if m.id],
        }

    def supervisor(state: State) -> dict:
        status = (
            f"- course worker: {'done' if state.get('course_notes') else 'not done yet'}\n"
            f"- docs worker: {'done' if state.get('docs_notes') else 'not done yet'}\n"
            f"- notes worker: {'done' if state.get('note_result') else 'not done yet'}"
        )
        route = Route.model_validate(
            router.invoke([SystemMessage(SUPERVISOR_PROMPT.format(status=status)), *history(state)])
        )
        next_step = route.next_step
        # a worker never runs twice for the same question
        if next_step == "course_worker" and state.get("course_notes"):
            next_step = "answer"
        if next_step == "docs_worker" and state.get("docs_notes"):
            next_step = "answer"
        if next_step == "notes_worker" and state.get("note_result"):
            next_step = "answer"
        return {"next_step": next_step}

    # only the final text of a worker is kept
    def course_node(state: State) -> dict:
        result = course_worker.invoke({"messages": history(state)})
        return {"course_notes": result["messages"][-1].text or NO_RESULTS}

    def docs_node(state: State) -> dict:
        result = docs_worker.invoke({"messages": history(state)})
        return {"docs_notes": result["messages"][-1].text or NO_RESULTS}

    def notes_node(state: State) -> dict:
        prompt = NOTES_WORKER_PROMPT.format(
            course_notes=state.get("course_notes") or "(not searched)",
            docs_notes=state.get("docs_notes") or "(not searched)",
        )
        note = Note.model_validate(note_writer.invoke([SystemMessage(prompt), *history(state)]))
        return {"note_draft": note.model_dump()}

    # Separate from the draft node: after an interrupt LangGraph reruns the node from the top,
    # and the draft must not be written again.
    async def save_note_node(state: State) -> dict:
        draft = state["note_draft"]
        approved = interrupt(draft)  # pauses here until the intern answers yes or no
        if not approved:
            return {"note_result": "The intern chose not to save the note. Nothing was saved."}
        return {"note_result": await save_note(draft["title"], draft["content"])}

    async def answer(state: State, runtime: Runtime) -> dict:
        facts = []
        if runtime.store is not None:
            facts = await list_facts(runtime.store, state.get("user_id") or "default")
        prompt = ANSWER_PROMPT.format(
            course_notes=state.get("course_notes") or "(not searched)",
            docs_notes=state.get("docs_notes") or "(not searched)",
            note_result=state.get("note_result") or "(no note requested)",
            memories="\n".join(f"- {fact['text']}" for fact in facts) or "(nothing yet)",
        )
        response = await llm.ainvoke([SystemMessage(prompt), *history(state)])
        # clear the worker results for the next question
        return {
            "messages": [response],
            "course_notes": "",
            "docs_notes": "",
            "note_draft": {},
            "note_result": "",
        }

    async def remember(state: State, runtime: Runtime) -> dict:
        # Looks only at the intern's own latest message, never at tool results or web pages,
        # so text from the internet can't write into the intern's memory.
        if runtime.store is None:
            return {}
        user_id = state.get("user_id") or "default"
        last_message = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
        )
        if last_message is None:
            return {}
        known = await list_facts(runtime.store, user_id)
        prompt = MEMORY_PROMPT.format(
            known="\n".join(f"- {fact['text']}" for fact in known) or "(nothing yet)"
        )
        result = Facts.model_validate(
            await fact_finder.ainvoke([SystemMessage(prompt), last_message])
        )
        await add_facts(runtime.store, user_id, result.facts)
        return {}

    def pick_worker(state: State) -> NextStep:
        return state["next_step"]  # pyrefly: ignore[bad-return]

    builder = StateGraph(State)  # pyrefly: ignore[bad-specialization]
    builder.add_node("summarize", summarize)
    builder.add_node("supervisor", supervisor)
    builder.add_node("course_worker", course_node)
    builder.add_node("docs_worker", docs_node)
    builder.add_node("notes_worker", notes_node)
    builder.add_node("save_note", save_note_node)
    builder.add_node("answer", answer)
    builder.add_node("remember", remember)

    builder.add_conditional_edges(START, needs_summary)
    builder.add_edge("summarize", "supervisor")
    builder.add_conditional_edges("supervisor", pick_worker)
    builder.add_edge("course_worker", "supervisor")
    builder.add_edge("docs_worker", "supervisor")
    builder.add_edge("notes_worker", "save_note")
    builder.add_edge("save_note", "supervisor")
    builder.add_edge("answer", "remember")
    builder.add_edge("remember", END)

    return builder.compile(checkpointer=checkpointer, store=store)
