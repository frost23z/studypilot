from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from api.sources import DOCUMENT_TYPES

router = APIRouter(prefix="/documents", tags=["documents"])


def get_documents(request: Request) -> Path:
    return request.app.state.documents


Documents = Annotated[Path, Depends(get_documents)]


def locate(folder: Path, filename: str) -> Path | None:
    """The file, only if it is directly in the folder and of a type that can be shown."""
    try:
        folder = folder.resolve()
        path = (folder / filename).resolve()  # follows links, so a link out of the folder fails
        if path.parent == folder and path.suffix.lower() in DOCUMENT_TYPES and path.is_file():
            return path
    except ValueError:  # for example a null byte in the name
        return None
    return None


@router.get("/{filename}")
def get_document(filename: str, documents: Documents) -> FileResponse:
    """One course file, for the browser to show. PDFs open at a page with #page=N."""
    path = locate(documents, filename)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return FileResponse(
        path,
        media_type=DOCUMENT_TYPES[path.suffix.lower()],
        filename=path.name,
        content_disposition_type="inline",  # show it in the browser, do not download it
    )
