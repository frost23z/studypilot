# https://aistudio.google.com/docs/embeddings
# https://docs.langchain.com/oss/python/integrations/embeddings
# https://docs.langchain.com/oss/python/integrations/embeddings/google_generative_ai
# https://docs.langchain.com/oss/python/deepagents/rag

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import SecretStr

from core.config import get_settings


def get_embeddings(api_key: SecretStr) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=get_settings().GOOGLE_EMBEDDING_MODEL,
        api_key=api_key.get_secret_value(),
        output_dimensionality=get_settings().EMBEDDING_DIMENSION,
    )
