from collections.abc import Iterable

from src.config.settings import settings


class _EmbeddingFn:
    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        p = self.provider
        if p == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings

                return OpenAIEmbeddings(
                    model=self.model,
                    api_key=settings.openai_api_key or None,
                    base_url=settings.openai_base_url or None,
                ).embed_documents(list(texts))
            except Exception as e:
                from src.utils.logger import get_logger
                get_logger(__name__).error("OpenAI embedding failure", error=str(e))
                return []
        if p == "google":
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                return GoogleGenerativeAIEmbeddings(
                    model=self.model,
                    google_api_key=settings.google_api_key or None
                ).embed_documents(
                    list(texts)
                )
            except Exception as e:
                from src.utils.logger import get_logger
                get_logger(__name__).error("Google embedding failure", error=str(e))
                return []
        return []

    def embed_query(self, text: str) -> list[float]:
        res = self.embed_documents([text])
        return res[0] if res else []


def get_embedding_fn() -> _EmbeddingFn:
    return _EmbeddingFn(settings.embeddings_provider, settings.embeddings_model)
