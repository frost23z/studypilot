from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class NoteRow(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    content: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


def to_dict(row: NoteRow) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "content": row.content,
        "created_at": row.created_at.replace(tzinfo=UTC).isoformat(),
        "updated_at": row.updated_at.replace(tzinfo=UTC).isoformat(),
    }


class NotesStore:
    def __init__(self, db_path: str | Path) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)

    def add(self, title: str, content: str) -> dict:
        title = title.strip()
        content = content.strip()
        if not title or not content:
            message = "A note needs a title and some content."
            raise ValueError(message)
        saved_at = now()
        row = NoteRow(title=title, content=content, created_at=saved_at, updated_at=saved_at)
        with Session(self.engine) as session, session.begin():
            session.add(row)
            session.flush()  # gives the row its id
            return to_dict(row)

    def list(self) -> list[dict]:
        with Session(self.engine) as session:
            rows = session.scalars(select(NoteRow).order_by(NoteRow.id.desc()))
            return [to_dict(row) for row in rows]

    def get(self, note_id: int) -> dict | None:
        with Session(self.engine) as session:
            row = session.get(NoteRow, note_id)
            return to_dict(row) if row else None

    def update(self, note_id: int, title: str, content: str) -> dict | None:
        title = title.strip()
        content = content.strip()
        if not title or not content:
            message = "A note needs a title and some content."
            raise ValueError(message)
        with Session(self.engine) as session, session.begin():
            row = session.get(NoteRow, note_id)
            if row is None:
                return None
            row.title = title
            row.content = content
            row.updated_at = now()
            return to_dict(row)

    def delete(self, note_id: int) -> bool:
        with Session(self.engine) as session, session.begin():
            row = session.get(NoteRow, note_id)
            if row is None:
                return False
            session.delete(row)
            return True
