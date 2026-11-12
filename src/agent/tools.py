# https://docs.langchain.com/oss/python/langchain/tools

from collections.abc import Callable

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.vectorstores import VectorStore
from langchain_tavily import TavilySearch

from agent.prompts import NO_RESULTS

OFFICIAL_SITES = {
    "python": ["docs.python.org"],
    "django": ["docs.djangoproject.com"],
    "django rest framework": ["django-rest-framework.org"],
    "flask": ["flask.palletsprojects.com"],
    "go": ["go.dev", "pkg.go.dev"],
    "beego": ["beego.wiki", "pkg.go.dev"],
    "html": ["developer.mozilla.org"],
    "css": ["developer.mozilla.org"],
    "javascript": ["developer.mozilla.org"],
    "typescript": ["typescriptlang.org"],
    "node.js": ["nodejs.org"],
    "postgresql": ["postgresql.org"],
    "postgis": ["postgis.net"],
    "pgvector": ["github.com"],  # the docs are the README
    "pandas": ["pandas.pydata.org"],
    "scrapy": ["docs.scrapy.org"],
    "playwright": ["playwright.dev"],
    "pytest": ["docs.pytest.org"],
    "langchain": ["docs.langchain.com"],
    "langgraph": ["docs.langchain.com"],
}


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


def make_docs_tool(search: TavilySearch):
    @tool(
        description=(
            "Search the official documentation of a technology. "
            f"Known technologies: {', '.join(OFFICIAL_SITES)}. "
            "Use the technology name exactly as listed and a short English query."
        )
    )
    def search_official_docs(technology: str, query: str) -> str:
        sites = OFFICIAL_SITES.get(technology.lower())
        args: dict = {"query": query}
        if sites:
            args["include_domains"] = sites  # only official sites
        try:
            response = search.invoke(args)
        except Exception as error:
            # let the model see the error instead of crashing the graph
            return f"Official docs search failed: {error}"
        # TavilySearch does not raise on failure, it returns {"error": ...}
        if "results" not in response:
            return f"Official docs search failed: {response.get('error', response)}"
        if not response["results"]:
            return NO_RESULTS
        label = "official docs" if sites else "web (unofficial)"
        return "\n\n".join(f"[{label}: {r['url']}]\n{r['content']}" for r in response["results"])

    return search_official_docs
