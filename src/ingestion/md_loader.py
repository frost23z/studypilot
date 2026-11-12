from pathlib import Path

from langchain_core.documents import Document


def load_markdown(file_path: str | Path) -> list[Document]:
    path = Path(file_path)
    return [
        Document(
            page_content=Path(file_path).read_text(encoding="utf-8"),
            metadata={"source": path.name, "format": "markdown"},
        )
    ]
