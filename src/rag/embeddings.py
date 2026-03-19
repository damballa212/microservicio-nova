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
                # Leer API key del admin panel primero
                _api_key = settings.openai_api_key or None
                _base_url = settings.openai_base_url or None
                try:
                    from src.models.admin import admin_repo, CredentialProvider
                    cred = admin_repo.get_default_credential(CredentialProvider.OPENROUTER)
                    if cred:
                        _api_key, _base_url = cred
                        _base_url = _base_url or "https://openrouter.ai/api/v1"
                except Exception:
                    pass
                return OpenAIEmbeddings(
                    model=self.model,
                    api_key=_api_key,
                    base_url=_base_url,
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
    _model = settings.embeddings_model
    try:
        from src.models.admin import admin_repo
        cfg = admin_repo.get_config("embeddings_model")
        if cfg and cfg.value:
            _model = cfg.value
    except Exception:
        pass
    return _EmbeddingFn(settings.embeddings_provider, _model)
