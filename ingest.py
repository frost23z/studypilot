from pathlib import Path

from core.config import get_settings
from embedding.gemini_embedding import get_embeddings
from ingestion.chunker import chunk_documents
from ingestion.pdf_loader import load_pdf
from vector_store.chroma_store import get_vector_store


def ingest_pdfs():
    input_dir = Path("documents")
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        return 0

    vector_store = get_vector_store(get_embeddings(get_settings().GOOGLE_API_KEYS[0]))

    total_chunks = 0
    for pdf_path in pdf_files:
        chunks = chunk_documents(load_pdf(pdf_path))
        vector_store.add_documents(chunks)  # embeds with the store's embedding model
        total_chunks += len(chunks)
        print(f"Indexed {pdf_path.name}: {len(chunks)} chunks")
    print(f"Total chunks indexed: {total_chunks}")


if __name__ == "__main__":
    ingest_pdfs()
