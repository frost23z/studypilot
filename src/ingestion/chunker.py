# https://docs.langchain.com/oss/python/integrations/splitters#text-structure-based

import html

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(
    documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 200
) -> list[Document]:
    # Unescape HTML entities
    cleaned_documents = [
        Document(
            page_content=html.unescape(document.page_content),
            metadata=document.metadata.copy(),
        )
        for document in documents
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_documents(cleaned_documents)
