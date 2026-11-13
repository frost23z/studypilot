from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from notes.store import NotesStore

router = APIRouter(prefix="/notes", tags=["notes"])


def get_store(request: Request) -> NotesStore:
    return request.app.state.store


Store = Annotated[NotesStore, Depends(get_store)]


class NoteIn(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    created_at: str
    updated_at: str


def not_found(note_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Note {note_id} not found.")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_note(body: NoteIn, store: Store) -> NoteOut:
    try:
        return NoteOut(**store.add(body.title, body.content))
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("")
def list_notes(store: Store) -> list[NoteOut]:
    return [NoteOut(**note) for note in store.list()]


@router.get("/{note_id}")
def get_note(note_id: int, store: Store) -> NoteOut:
    note = store.get(note_id)
    if note is None:
        raise not_found(note_id)
    return NoteOut(**note)


@router.put("/{note_id}")
def update_note(note_id: int, body: NoteIn, store: Store) -> NoteOut:
    try:
        note = store.update(note_id, body.title, body.content)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    if note is None:
        raise not_found(note_id)
    return NoteOut(**note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, store: Store) -> None:
    if not store.delete(note_id):
        raise not_found(note_id)
