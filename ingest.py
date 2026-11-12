import hashlib
from pathlib import Path

from chromadb.api.types import Where

from core.config import get_settings
from embedding.gemini_embedding import get_embeddings
from ingestion.chunker import chunk_documents
from ingestion.manifest import IngestionManifest
from ingestion.md_loader import load_markdown
from ingestion.pdf_loader import load_pdf
from vector_store.chroma_store import get_vector_store

LOADERS = {".pdf": load_pdf, ".md": load_markdown}


def ingest_documents():
    input_dir = Path("documents")
    files = {p.name: p for p in sorted(input_dir.iterdir()) if p.suffix.lower() in LOADERS}
    if not files:
        return 0

    settings = get_settings()
    vector_store = get_vector_store(get_embeddings(settings.GOOGLE_API_KEYS[0]))
    manifest = IngestionManifest(Path(settings.CHROMA_PERSIST_DIRECTORY) / "manifest.sqlite3")
    indexed = manifest.hashes()

    # Files deleted from input_dir are also deleted from vector store and manifest on next run.
    for source in indexed.keys() - files.keys():
        vector_store.delete(where={"source": source})
        manifest.remove(source)
        print(f"Removed {source}")

    total_chunks = 0
    for source, path in files.items():
        try:
            with path.open("rb") as f:
                file_hash = hashlib.file_digest(f, "sha256").hexdigest()
            stale = {"$and": [{"source": source}, {"file_hash": {"$ne": file_hash}}]}
            if indexed.get(source) == file_hash:
                # any file half finished indexing is replaced with the new version.
                vector_store.delete(where=stale)
                print(f"Skipped {source} (unchanged)")
                continue

            chunks = chunk_documents(LOADERS[path.suffix.lower()](path))
            for chunk in chunks:
                chunk.metadata.update(source=source, file_hash=file_hash)
            ids = [f"{source}:{file_hash}:{i}" for i in range(len(chunks))]

            # Only embed new chunks
            version: Where = {"$and": [{"source": source}, {"file_hash": file_hash}]}
            stored = set(vector_store.get(where=version, include=[])["ids"])
            todo = [(i, c) for i, c in zip(ids, chunks, strict=True) if i not in stored]
            for start in range(0, len(todo), settings.EMBEDDING_BATCH_SIZE):
                batch = todo[start : start + settings.EMBEDDING_BATCH_SIZE]
                vector_store.add_documents([c for _, c in batch], ids=[i for i, _ in batch])

            missing = set(ids) - set(vector_store.get(where=version, include=[])["ids"])
            if missing:
                msg = f"{len(missing)} chunks missing after indexing"
                raise RuntimeError(msg)
            manifest.save(source, file_hash)
            vector_store.delete(where=stale)
            total_chunks += len(chunks)
            print(f"Indexed {source}: {len(chunks)} chunks")
        except Exception as e:
            print(f"Failed {source}: {e} (will retry next run)")
    print(f"Total chunks indexed: {total_chunks}")


if __name__ == "__main__":
    ingest_documents()
