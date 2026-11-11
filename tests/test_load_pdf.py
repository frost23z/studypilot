# https://docs.pytest.org/en/stable/example/markers.html#registering-markers

import shutil
from pathlib import Path

import pytest

from ingestion.chunker import chunk_documents
from ingestion.pdf_loader import load_pdf


@pytest.mark.slow
def test_load_pdf() -> None:
    input_dir = Path(__file__).parent.parent / "documents"
    output_dir = Path(__file__).parent / "output"
    chunks_output_dir = Path(__file__).parent / "output_chunks"

    shutil.rmtree(output_dir, ignore_errors=True)
    shutil.rmtree(chunks_output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.glob("*.pdf"))
    assert len(pdf_files) > 0, "No PDF files found in the input directory."

    for pdf_file in pdf_files:
        documents = load_pdf(pdf_file)
        assert documents, f"Failed to load text from {pdf_file.name}"

        output_file = output_dir / f"{pdf_file.stem}.txt"
        with Path.open(output_file, "w", encoding="utf-8") as file:
            file.write(f"Extracted pages: {len(documents)}\n\n")
            for document in documents:
                file.write(f"{'=' * 80}\n")
                file.write(f"Page {document.metadata['page']}:\n")
                file.write(f"{'=' * 80}\n")
                file.write(f"Page content length: {len(document.page_content)} characters\n")
                file.write(f"{'-' * 80}\n")
                file.write(document.page_content + "\n")
                file.write(f"{'-' * 80}\n")
                file.write("Metadata:\n")
                file.write(f"{'-' * 80}\n")
                file.write(str(document.metadata) + "\n")
                file.write("\n\n")

        chunks = chunk_documents(documents)
        assert chunks, f"Failed to chunk documents from {pdf_file.name}"

        chunks_output_file = chunks_output_dir / f"{pdf_file.stem}_chunks.txt"
        with Path.open(chunks_output_file, "w", encoding="utf-8") as file:
            for i, chunk in enumerate(chunks):
                file.write(f"{'=' * 80}\n")
                file.write(f"Chunk {i}:\n")
                file.write(f"{'=' * 80}\n")
                file.write(f"Chunk content length: {len(chunk.page_content)} characters\n")
                file.write(f"{'-' * 80}\n")
                file.write(chunk.page_content + "\n")
                file.write(f"{'-' * 80}\n")
                file.write("Metadata:\n")
                file.write(f"{'-' * 80}\n")
                file.write(str(chunk.metadata) + "\n")
                file.write("\n\n")
