"""Find the course files an answer cites, so the page can link to them.

The agent writes citations as [file, page N], or [file] when the file has no pages. Only a
citation of a file that really is in the documents folder counts as a source.
"""

import re
from pathlib import Path

from pydantic import BaseModel

# The files that can be shown, and how a browser should show them.
DOCUMENT_TYPES = {".pdf": "application/pdf", ".md": "text/plain"}

BRACKETS = re.compile(r"\[([^\[\]]+)\]")
PAGE = r",\s*pages?\s+(\d+)"


class Source(BaseModel):
    file: str
    page: int | None = None  # pages start at 1. Markdown files have none.


def list_documents(folder: Path) -> dict[str, str]:
    """The files that can be shown, as {lowercase name: real name}."""
    if not folder.is_dir():
        return {}
    return {
        path.name.lower(): path.name
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in DOCUMENT_TYPES
    }


def find_sources(text: str, folder: Path) -> list[Source]:
    """The cited files of an answer, in the order they are cited, without repeats."""
    files = list_documents(folder)
    found: dict[tuple[str, int | None], Source] = {}
    for brackets in BRACKETS.findall(text):
        for citation in brackets.split(";"):  # [a.pdf, page 1; b.pdf, page 2]
            citation = citation.strip().lower()
            for lower_name, name in files.items():
                if citation == lower_name:
                    key = (name, None)
                elif match := re.fullmatch(re.escape(lower_name) + PAGE, citation):
                    key = (name, int(match[1]))
                else:
                    continue
                found.setdefault(key, Source(file=name, page=key[1]))
                break
    return list(found.values())
