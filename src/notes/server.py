from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from notes.store import NotesStore


def build_server(store: NotesStore) -> FastMCP:
    server = FastMCP(
        "StudyPilot Notes",
        instructions="Save and manage the intern's study notes.",
    )

    @server.tool
    def add_note(title: str, content: str) -> dict:
        """Save a new note. Returns the saved note with its id."""
        return store.add(title, content)

    @server.tool
    def list_notes() -> list[dict]:
        """List all notes, newest first."""
        return store.list()

    @server.tool
    def get_note(note_id: int) -> dict:
        """Get one note by its id."""
        note = store.get(note_id)
        if note is None:
            message = f"Note {note_id} not found."
            raise ToolError(message)
        return note

    @server.tool
    def update_note(note_id: int, title: str, content: str) -> dict:
        """Replace the title and content of an existing note."""
        note = store.update(note_id, title, content)
        if note is None:
            message = f"Note {note_id} not found."
            raise ToolError(message)
        return note

    @server.tool
    def delete_note(note_id: int) -> str:
        """Delete a note by its id."""
        if not store.delete(note_id):
            message = f"Note {note_id} not found."
            raise ToolError(message)
        return f"Note {note_id} deleted."

    return server
