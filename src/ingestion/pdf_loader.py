# https://docs.langchain.com/oss/python/integrations/document_loaders#pdfs
# https://github.com/opendataloader-project/langchain-opendataloader-pdf

from pathlib import Path

from langchain_core.documents import Document
from langchain_opendataloader_pdf import OpenDataLoaderPDFLoader


def load_pdf(file_path: str | Path) -> list[Document]:
    loader = OpenDataLoaderPDFLoader(
        file_path=str(file_path),
        format="markdown",
        quiet=True,
    )

    return loader.load()
