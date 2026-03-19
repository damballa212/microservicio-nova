"""
Embeddings module — soporta Google Gemini (gratis), Cohere (gratis), y OpenAI directo.
OpenRouter NO soporta embeddings así que no se usa aquí.
"""
from collections.abc import Iterable

from src.config.settings import settings


def _get_embedding_config() -> tuple[str, str]:
    """Lee embeddings_provider y embeddings_model de admin DB, fallback a settings."""
    provider = settings.embeddings_provider or "google"
    model = settings.embeddings_model or "models/text-embedding-004"
    try:
        from src.models.admin import admin_repo
        cfg_provider = admin_repo.get_config("embeddings_provider")
        cfg_model = admin_repo.get_config("embeddings_model")
        if cfg_provider and cfg_provider.value:
            provider = cfg_provider.value
        if cfg_model and cfg_model.value:
            model = cfg_model.value
    except Exception:
        pass
    return provider, model


class _EmbeddingFn:
    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        from src.utils.logger import get_logger
        log = get_logger(__name__)
        text_list = list(texts)
        p = self.provider

        # ── Google Gemini (gratis) ──────────────────────────────────────────
        if p == "google":
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                # Leer Google API key desde admin panel
                _api_key = settings.google_api_key or None
                try:
                    from src.models.admin import admin_repo, CredentialProvider
                    cred = admin_repo.get_default_credential(CredentialProvider.GOOGLE)
                    if cred:
                        _api_key = cred[0]
                except Exception:
                    pass
                return GoogleGenerativeAIEmbeddings(
                    model=self.model,
                    google_api_key=_api_key,
                ).embed_documents(text_list)
            except Exception as e:
                log.error("Google embedding failure", error=str(e))
                return []

        # ── Cohere (free tier) ─────────────────────────────────────────────
        if p == "cohere":
            try:
                from langchain_cohere import CohereEmbeddings
                _api_key = None
                try:
                    from src.models.admin import admin_repo, CredentialProvider
                    cred = admin_repo.get_default_credential(CredentialProvider.COHERE)
                    if cred:
                        _api_key = cred[0]
                except Exception:
                    pass
                if not _api_key:
                    import os
                    _api_key = os.environ.get("COHERE_API_KEY")
                return CohereEmbeddings(
                    model=self.model,
                    cohere_api_key=_api_key,
                ).embed_documents(text_list)
            except Exception as e:
                log.error("Cohere embedding failure", error=str(e))
                return []

        # ── OpenAI directo (NO OpenRouter) ─────────────────────────────────
        if p == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings
                _api_key = None
                try:
                    from src.models.admin import admin_repo, CredentialProvider
                    cred = admin_repo.get_default_credential(CredentialProvider.OPENAI)
                    if cred:
                        _api_key = cred[0]
                except Exception:
                    pass
                if not _api_key:
                    _api_key = settings.openai_api_key or None
                return OpenAIEmbeddings(
                    model=self.model,
                    api_key=_api_key,
                    # Sin base_url — OpenAI directo, no OpenRouter
                ).embed_documents(text_list)
            except Exception as e:
                log.error("OpenAI embedding failure", error=str(e))
                return []

        return []

    def embed_query(self, text: str) -> list[float]:
        res = self.embed_documents([text])
        return res[0] if res else []


def get_embedding_fn() -> _EmbeddingFn:
    provider, model = _get_embedding_config()
    return _EmbeddingFn(provider, model)
