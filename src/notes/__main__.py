from core.config import get_settings
from notes.server import build_server
from notes.store import NotesStore


def main() -> None:
    build_server(NotesStore(get_settings().NOTES_DB_PATH)).run(show_banner=False)


if __name__ == "__main__":
    main()
