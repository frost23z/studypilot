"""The list of chats (threads) of each person. The messages themselves live in the checkpointer."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

TITLE_LENGTH = 60


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ThreadRow(Base):
    __tablename__ = "threads"

    thread_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(index=True)
    title: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


def make_title(message: str) -> str:
    text = " ".join(message.split())
    if len(text) <= TITLE_LENGTH:
        return text
    return text[: TITLE_LENGTH - 1].rstrip() + "…"


def to_dict(row: ThreadRow) -> dict:
    return {
        "thread_id": row.thread_id,
        "title": row.title,
        "updated_at": row.updated_at.replace(tzinfo=UTC).isoformat(),
    }


class ThreadsStore:
    def __init__(self, db_path: str | Path) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)

    def touch(self, thread_id: str, user_id: str, message: str) -> None:
        """Note that a chat was used. The first message of a new chat becomes its title."""
        saved_at = now()
        with Session(self.engine) as session, session.begin():
            row = session.get(ThreadRow, thread_id)
            if row is None:
                session.add(
                    ThreadRow(
                        thread_id=thread_id,
                        user_id=user_id,
                        title=make_title(message) or "New chat",
                        created_at=saved_at,
                        updated_at=saved_at,
                    )
                )
            else:
                row.updated_at = saved_at  # the owner and title stay as they were

    def bump(self, thread_id: str) -> None:
        with Session(self.engine) as session, session.begin():
            if row := session.get(ThreadRow, thread_id):
                row.updated_at = now()

    def list(self, user_id: str) -> list[dict]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ThreadRow)
                .where(ThreadRow.user_id == user_id)
                .order_by(ThreadRow.updated_at.desc(), ThreadRow.created_at.desc())
            )
            return [to_dict(row) for row in rows]
