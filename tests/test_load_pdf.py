# https://docs.pytest.org/en/stable/example/markers.html#registering-markers

import shutil
from pathlib import Path

import pytest

from ingestion.pdf_loader import load_pdf


@pytest.mark.slow
def test_load_pdf() -> None:
    input_dir = Path(__file__).parent.parent / "documents"
    output_dir = Path(__file__).parent / "output"

    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

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
