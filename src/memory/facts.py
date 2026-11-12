"""Long-term memory: short facts about each user, kept across threads, in a LangGraph store."""

import uuid

from langgraph.store.base import BaseStore

MAX_FACTS = 20  # most facts kept per user_id
MAX_NEW_PER_QUESTION = 3  # most facts saved after one question
MAX_FACT_LENGTH = 200


def namespace(user_id: str) -> tuple[str, str]:
    return (user_id, "facts")


async def list_facts(store: BaseStore, user_id: str) -> list[dict]:
    items = await store.asearch(namespace(user_id), limit=MAX_FACTS)
    return [{"id": item.key, "text": item.value["text"]} for item in items]


async def add_facts(store: BaseStore, user_id: str, new_facts: list[str]) -> list[str]:
    """Save new facts, skipping blanks and repeats. Returns what was saved."""
    known = [fact["text"].lower() for fact in await list_facts(store, user_id)]
    saved = []
    for text in new_facts[:MAX_NEW_PER_QUESTION]:
        text = text.strip()[:MAX_FACT_LENGTH]
        if not text or text.lower() in known:
            continue
        if len(known) >= MAX_FACTS:
            break
        await store.aput(namespace(user_id), uuid.uuid4().hex, {"text": text})
        known.append(text.lower())
        saved.append(text)
    return saved


async def delete_fact(store: BaseStore, user_id: str, fact_id: str) -> bool:
    if await store.aget(namespace(user_id), fact_id) is None:
        return False
    await store.adelete(namespace(user_id), fact_id)
    return True
