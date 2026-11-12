from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class IndexedPdf(Base):
    __tablename__ = "indexed_pdfs"

    source: Mapped[str] = mapped_column(primary_key=True)
    file_hash: Mapped[str]


class IngestionManifest:
    def __init__(self, db_path: str | Path) -> None:
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)

    def hashes(self) -> dict[str, str]:
        with Session(self.engine) as session:
            return {row.source: row.file_hash for row in session.scalars(select(IndexedPdf))}

    def save(self, source: str, file_hash: str) -> None:
        with Session(self.engine) as session, session.begin():
            session.merge(IndexedPdf(source=source, file_hash=file_hash))

    def remove(self, source: str) -> None:
        with Session(self.engine) as session, session.begin():
            if row := session.get(IndexedPdf, source):
                session.delete(row)

    def active_filter(self) -> dict | None:
        hashes = list(self.hashes().values())
        return {"file_hash": {"$in": hashes}} if hashes else None
