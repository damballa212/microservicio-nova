"""
Configuración centralizada del proyecto.

Usa Pydantic Settings para cargar variables de entorno de forma tipada y validada.
Todas las configuraciones del chatbot se centralizan aquí para fácil mantenimiento.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración del chatbot cargada desde variables de entorno.

    Ejemplo de uso:
        from src.config import settings
        print(settings.redis_url)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Redis ===
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="URL de conexión a Redis"
    )

    # === OpenAI ===
    openai_api_key: str = Field(
        default="", description="API Key de OpenAI para Whisper y GPT-4 Vision"
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", description="Base URL de OpenAI (o OpenRouter)"
    )

    # === Google Gemini ===
    google_api_key: str = Field(default="", description="API Key de Google para Gemini")

    google_sheets_service_account_json: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON"),
        description="Ruta al JSON de Service Account para Google Sheets",
    )

    flowify_knowledge_search_path: str = Field(
        default="/api/conocimiento/search",
        validation_alias=AliasChoices("FLOWIFY_KNOWLEDGE_SEARCH_PATH"),
        description="Path del endpoint de búsqueda de conocimiento en Flowify",
    )

    flowify_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("FLOWIFY_API_KEY"),
        description="API key opcional para autenticación hacia Flowify",
    )

    flowify_api_token: str = Field(
        default="",
        validation_alias=AliasChoices("FLOWIFY_API_TOKEN"),
        description="Token Bearer opcional para autenticación hacia Flowify",
    )

    outbound_webhook_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("OUTBOUND_WEBHOOK_BASE_URL", "FLOWIFY_BASE_URL"),
        description="Base URL del sistema externo para webhooks",
    )
    outbound_webhook_path: str = Field(
        default="/webhooks/n8n/nova",
        validation_alias=AliasChoices("OUTBOUND_WEBHOOK_PATH"),
        description="Path del endpoint de webhook outbound",
    )
    outbound_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices("OUTBOUND_WEBHOOK_SECRET", "N8N_WEBHOOK_SECRET"),
        description="Secreto HMAC para firma opcional de webhook outbound",
    )

    # === Buffer ===
    buffer_wait_seconds: int = Field(
        default=10, description="Segundos a esperar para consolidar mensajes"
    )
    namespace_by_tenant: bool = Field(
        default=True, description="Si true, usa namespacing por tenant en memoria y buffer"
    )

    # === Memory ===
    memory_window_size: int = Field(
        default=4, description="Número de mensajes en memoria conversacional"
    )

    # === Pricing ===
    llm_pricing_input_per_1k: dict[str, float] = Field(
        default={
            "openai/gpt-4.1-mini": 0.0004,
            "gemini-1.5-flash": 0.1,
        },
        description="USD por 1k tokens de entrada por modelo",
    )
    llm_pricing_output_per_1k: dict[str, float] = Field(
        default={
            "openai/gpt-4.1-mini": 0.0016,
            "gemini-1.5-flash": 0.3,
        },
        description="USD por 1k tokens de salida por modelo",
    )
    llm_pricing_input_per_1k_overrides: dict[str, float] = Field(
        default={
            "openai:openai/gpt-4.1-mini": 0.0004,
            "openrouter:openai/gpt-4.1-mini": 0.0004,
        },
        description="Overrides por proveedor:modelo (ej. 'openrouter:openai/gpt-4.1-mini')",
    )
    llm_pricing_output_per_1k_overrides: dict[str, float] = Field(
        default={
            "openai:openai/gpt-4.1-mini": 0.0016,
            "openrouter:openai/gpt-4.1-mini": 0.0016,
        },
        description="Overrides por proveedor:modelo (ej. 'openrouter:openai/gpt-4.1-mini')",
    )

    # === Metrics Persistence ===
    metrics_ttl_seconds: int = Field(
        default=604800, description="TTL de métricas en Redis (por defecto 7 días)"
    )
    metrics_history_max_items: int = Field(
        default=200, description="Máximo de items en historial a retornar"
    )

    # === Alerts ===
    alerts_enabled: bool = Field(default=True, description="Habilita alertas de umbral")
    alert_max_duration_ms: int = Field(default=3000, description="Duración máxima por nodo")
    alert_max_total_tokens: int = Field(default=8000, description="Tokens máximos por nodo")

    # === Distributed Execution ===
    execution_role: Literal["all", "api", "worker"] = Field(
        default="all",
        description="Rol del proceso: api (solo HTTP/WS), worker (solo workers), all (ambos)",
    )
    execution_queue_enabled: bool = Field(
        default=False,
        description="Si true, encola ejecuciones en Redis Streams y las procesa con workers",
    )
    execution_stream_key: str = Field(
        default="neural:executions",
        description="Stream Redis para ejecuciones encoladas",
    )
    execution_stream_group: str = Field(
        default="neural-workers",
        description="Consumer group Redis Streams para workers",
    )
    execution_worker_concurrency: int = Field(
        default=16,
        description="Concurrencia de workers por proceso",
    )
    redis_events_channel: str = Field(
        default="neural:events",
        description="Canal PubSub Redis para eventos del dashboard",
    )
    redis_events_bridge_enabled: bool = Field(
        default=True,
        description="Si true, el proceso API reemite eventos desde Redis hacia WebSockets",
    )

    # === RAG Ingest ===
    rag_upload_max_bytes: int = Field(
        default=25 * 1024 * 1024,
        description="Tamaño máximo de archivo para ingest (bytes)",
    )
    rag_allowed_mime_types: list[str] = Field(
        default=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain",
            "text/csv",
        ],
        description="Lista de MIME permitidos para ingest",
    )
    rag_ingest_stream_key: str = Field(
        default="neural:rag_ingest",
        description="Stream Redis para tareas de ingest RAG",
    )
    rag_ingest_stream_group: str = Field(
        default="rag-workers",
        description="Consumer group Redis Streams para ingest",
    )
    rag_ingest_worker_concurrency: int = Field(
        default=4,
        description="Concurrencia de workers de ingest",
    )

    # === RAG Storage & Retrieval ===
    postgres_url: str = Field(default="", description="URL de conexión a Postgres para RAG")
    pg_schema: str = Field(default="public", description="Schema de Postgres")
    pgvector_table: str = Field(default="documents_pg", description="Tabla vectorial de RAG")
    pg_semantic_memory_table: str = Field(default="semantic_episodes", description="Tabla de episodios semánticos")
    pg_document_rows_table: str = Field(
        default="document_rows", description="Tabla de filas tabulares para Excel/CSV"
    )
    pg_document_metadata_table: str = Field(
        default="document_metadata", description="Tabla de metadatos de documentos"
    )
    embeddings_provider: Literal["openai", "google", "cohere"] = Field(
        default="google", description="Proveedor de embeddings (google=gratis, cohere=free tier, openai=pago directo)"
    )
    embeddings_model: str = Field(
        default="models/text-embedding-004", description="Modelo de embeddings"
    )
    cohere_api_key: str = Field(
        default="", validation_alias=AliasChoices("COHERE_API_KEY"), description="API Key Cohere"
    )
    rag_search_top_k: int = Field(default=10, description="Top K por búsqueda RAG")
    rag_reranker_enabled: bool = Field(default=True, description="Habilita reranker Cohere")
    rag_cleanup_interval_minutes: int = Field(
        default=15, description="Intervalo de limpieza y reconciliación (minutos)"
    )

    # === Semantic Episodes (Conversational Memory) ===
    semantic_episode_stream_key: str = Field(
        default="neural:semantic_episodes",
        description="Stream Redis para trabajos de episodios semánticos",
    )
    semantic_episode_stream_group: str = Field(
        default="semantic-workers",
        description="Consumer group Redis Streams para episodios semánticos",
    )
    semantic_episode_worker_concurrency: int = Field(
        default=4, description="Concurrencia de workers de episodios semánticos"
    )
    semantic_episode_window_size: int = Field(
        default=15, description="Número de mensajes a consolidar por episodio"
    )
    semantic_episode_trigger_every_messages: int = Field(
        default=12,
        description="Umbral de mensajes para encolar consolidación de episodio",
    )
    semantic_episode_inline_enabled: bool = Field(
        default=True,
        description="Si true, inserta micro-episodio por turno (usuario/asistente)",
    )
    semantic_episode_inactivity_minutes: int = Field(
        default=20,
        description="Minutos de inactividad para disparar consolidación de episodio",
    )

    # === Server ===
    port: int = Field(default=8000, description="Puerto del servidor")
    host: str = Field(default="0.0.0.0", description="Host del servidor")
    environment: Literal["development", "production"] = Field(
        default="development", description="Ambiente de ejecución"
    )

    # === Notifications ===
    notification_email: str = Field(
        default="", description="Email para notificaciones de escalamiento"
    )
    notification_webhook_url: str = Field(default="", description="Webhook URL para notificaciones")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Nivel de logs"
    )

    # === Security ===
    cors_allowed_origins: str = Field(
        default="",
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS"),
        description="Lista de orígenes permitidos separados por coma (CORS)",
    )

    # === Observability (Phoenix + OpenTelemetry) ===
    phoenix_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("PHOENIX_ENABLED"),
        description="Habilita exportación de trazas a Phoenix via OpenTelemetry",
    )
    phoenix_project_name: str = Field(
        default="chatbot-whatsapp",
        validation_alias=AliasChoices("PHOENIX_PROJECT_NAME"),
        description="Nombre de proyecto/servicio para agrupar trazas",
    )
    phoenix_collector_endpoint: str = Field(
        default="http://localhost:4317",
        validation_alias=AliasChoices(
            "PHOENIX_COLLECTOR_ENDPOINT",
            "PHOENIX_ENDPOINT",
            "COLLECTOR_ENDPOINT",
        ),
        description="Endpoint OTLP para exportar trazas (grpc o http/protobuf)",
    )
    phoenix_protocol: Literal["grpc", "http/protobuf"] = Field(
        default="grpc",
        validation_alias=AliasChoices("PHOENIX_PROTOCOL"),
        description="Protocolo OTLP para exportación de trazas",
    )
    phoenix_auto_instrument: bool = Field(
        default=True,
        validation_alias=AliasChoices("PHOENIX_AUTO_INSTRUMENT"),
        description="Habilita auto-instrumentación (OpenInference) si está instalada",
    )
    phoenix_batch: bool = Field(
        default=True,
        validation_alias=AliasChoices("PHOENIX_BATCH"),
        description="Usa BatchSpanProcessor para exportación en background",
    )

    @field_validator("outbound_webhook_base_url")
    @classmethod
    def remove_trailing_slash2(cls, v: str) -> str:
        return v.rstrip("/") if v else v

    @property
    def is_development(self) -> bool:
        """Verifica si está en modo desarrollo."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Verifica si está en modo producción."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Obtiene la instancia de configuración (cacheada).

    Usa lru_cache para evitar recargar el archivo .env en cada llamada.
    """
    return Settings()


# Instancia global de configuración
settings = get_settings()
