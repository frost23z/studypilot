# https://docs.langchain.com/oss/python/langchain/tools

from collections.abc import Callable

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.vectorstores import VectorStore

from agent.prompts import NO_RESULTS


def format_passages(docs: list[Document]) -> str:
    """Turn search hits into text the model can read and cite as [file, page N]."""
    if not docs:
        return NO_RESULTS
    passages = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page")  # markdown files have no pages
        label = f"{source}, page {page}" if page is not None else source
        passages.append(f"[{label}]\n{doc.page_content}")
    return "\n\n".join(passages)


def make_retrieve_tool(
    vector_store: VectorStore,
    top_k: int,
    search_filter: Callable[[], dict | None] | None = None,
):
    @tool
    def retrieve_course_materials(query: str) -> str:
        """Search the course materials and return passages with their [file, page]."""
        kwargs: dict = {"k": top_k}
        # only search files that are still indexed
        if search_filter and (metadata_filter := search_filter()):
            kwargs["filter"] = metadata_filter
        return format_passages(vector_store.similarity_search(query, **kwargs))

    return retrieve_course_materials
