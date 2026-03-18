"""
Punto de entrada de la aplicación FastAPI.

Configura la aplicación, middleware, y lifecycle hooks.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.utils.logger import get_logger, setup_logging
from src.utils.redis_client import redis_client

# Configurar logging
setup_logging()
logger = get_logger(__name__)

_tracing_initialized = False


def _is_phoenix_enabled() -> bool:
    if settings.phoenix_enabled:
        return True
    return bool(
        os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
        or os.getenv("PHOENIX_ENDPOINT")
        or os.getenv("COLLECTOR_ENDPOINT")
    )


def _phoenix_endpoint() -> str:
    return (
        os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
        or os.getenv("PHOENIX_ENDPOINT")
        or os.getenv("COLLECTOR_ENDPOINT")
        or settings.phoenix_collector_endpoint
    )


def _phoenix_protocol(endpoint: str) -> Literal["http/protobuf", "grpc"] | None:
    explicit = os.getenv("PHOENIX_PROTOCOL")
    if explicit:
        v = explicit.strip().lower()
        if v in {"http/protobuf", "http-protobuf", "http_protobuf"}:
            return "http/protobuf"
        if v in {"grpc", "grpc/protobuf", "grpc-protobuf", "grpc_protobuf"}:
            return "grpc"
        return None
    if ":6006" in endpoint:
        return "http/protobuf"
    v2 = settings.phoenix_protocol
    if v2 in {"grpc", "http/protobuf"}:
        return v2
    return None


def _setup_tracing_early() -> None:
    global _tracing_initialized
    if _tracing_initialized or not _is_phoenix_enabled():
        return

    endpoint = _phoenix_endpoint()
    protocol = _phoenix_protocol(endpoint)
    project_name = os.getenv("PHOENIX_PROJECT_NAME") or settings.phoenix_project_name

    try:
        from phoenix.otel import register

        register(
            project_name=project_name,
            endpoint=endpoint,
            protocol=protocol,
            auto_instrument=settings.phoenix_auto_instrument,
            batch=settings.phoenix_batch,
        )
    except Exception as e:
        logger.warning("Phoenix tracing no inicializado", error=str(e))
        return

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass

    _tracing_initialized = True


def _instrument_fastapi(app: FastAPI) -> None:
    if not _tracing_initialized:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:
        logger.warning("No se pudo instrumentar FastAPI", error=str(e))


_setup_tracing_early()


def _load_runtime_deps():
    from src.api.router import router
    from src.api.test_router import test_router
    from src.api.metrics_router import metrics_router
    from src.api.rag_router import rag_router
    from src.events.emitter import _ORIGIN_ID, event_emitter
    from src.graph.builder import start_worker_pool, stop_worker_pool
    from src.memory.episodes_worker import start_semantic_worker_pool, stop_semantic_worker_pool
    from src.rag.worker import start_rag_worker_pool, stop_rag_worker_pool

    return (
        router,
        test_router,
        metrics_router,
        rag_router,
        _ORIGIN_ID,
        event_emitter,
        start_worker_pool,
        stop_worker_pool,
        start_rag_worker_pool,
        stop_rag_worker_pool,
        start_semantic_worker_pool,
        stop_semantic_worker_pool,
    )


(
    router,
    test_router,
    metrics_router,
    rag_router,
    _ORIGIN_ID,
    event_emitter,
    start_worker_pool,
    stop_worker_pool,
    start_rag_worker_pool,
    stop_rag_worker_pool,
    start_semantic_worker_pool,
    stop_semantic_worker_pool,
) = _load_runtime_deps()


async def _redis_events_bridge(stop_event: asyncio.Event) -> None:
    pubsub = None
    try:
        pubsub = await redis_client.get_pubsub()
        await pubsub.subscribe(settings.redis_events_channel)
        while not stop_event.is_set():
            try:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except Exception:
                msg = None
            if not msg:
                await asyncio.sleep(0.05)
                continue
            data = msg.get("data")
            if not data:
                continue
            try:
                payload = json.loads(data)
            except Exception:
                continue
            try:
                meta = payload.get("meta") if isinstance(payload, dict) else None
                if isinstance(meta, dict) and meta.get("origin") == _ORIGIN_ID:
                    continue
            except Exception:
                pass
            try:
                event_emitter.ingest(payload)
            except Exception:
                pass
            try:
                await event_emitter.broadcast(payload)
            except Exception:
                pass
    except Exception:
        return
    finally:
        try:
            if pubsub is not None:
                await pubsub.unsubscribe(settings.redis_events_channel)
                await pubsub.close()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle hooks de la aplicación.

    Startup: Inicializa conexiones
    Shutdown: Cierra conexiones
    """
    # === Startup ===
    logger.info(
        "Iniciando Chatbot WhatsApp",
        environment=settings.environment,
        version="1.0.0",
    )

    _instrument_fastapi(app)

    # Verificar conexión Redis
    try:
        client = await redis_client.get_client()
        await client.ping()
        logger.info("Conexión Redis establecida")
    except Exception as e:
        logger.warning("Redis no disponible", error=str(e))

    bridge_stop = asyncio.Event()
    bridge_task: asyncio.Task | None = None
    if settings.redis_events_bridge_enabled and settings.execution_role in {"all", "api"}:
        bridge_task = asyncio.create_task(_redis_events_bridge(bridge_stop))

    try:
        await start_worker_pool()
    except Exception:
        pass
    try:
        await start_rag_worker_pool()
    except Exception:
        pass
    try:
        await start_semantic_worker_pool()
    except Exception:
        pass

    yield

    # === Shutdown ===
    logger.info("Cerrando Chatbot WhatsApp")

    try:
        await stop_worker_pool()
    except Exception:
        pass
    try:
        await stop_rag_worker_pool()
    except Exception:
        pass
    try:
        await stop_semantic_worker_pool()
    except Exception:
        pass

    if bridge_task is not None:
        bridge_stop.set()
        try:
            bridge_task.cancel()
        except Exception:
            pass
        try:
            await bridge_task
        except Exception:
            pass

    # Cerrar conexiones
    await redis_client.close()

    logger.info("Conexiones cerradas")


# Crear aplicación
app = FastAPI(
    title="Chatbot WhatsApp con LangGraph",
    description="""
    Chatbot inteligente para WhatsApp migrado desde n8n.

    ## Características
    - 🤖 LangGraph para flujo de estados
    - 🎤 Transcripción de audio (Whisper)
    - 🖼️ Análisis de imágenes (GPT-4 Vision)
    - 💬 Memoria conversacional
    - 📱 Integración por webhooks
    - 🧪 Sistema de Testing integrado

    ## Endpoints
    - `POST /webhook/inbound`: Recibe webhooks de entrada
    - `GET /health`: Health check
    - `GET /graph/diagram`: Diagrama del grafo

    ## Testing
    - `POST /test/chat`: Probar chat sin proveedor externo
    - `POST /test/node/{name}`: Probar nodo individual
    - `GET /test/nodes`: Listar nodos disponibles
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Configurar CORS - restringido en producción
# Configurar CORS - restringido en producción
cors_origins = ["*"] if settings.is_development else [
    "https://flowify.ai",
    "https://app.flowify.ai",
    "https://dashboard.flowify.ai",
]

# Agregar orígenes configurados dinámicamente
if settings.cors_allowed_origins:
    extra_origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    cors_origins.extend(extra_origins)
elif settings.is_production:
    # Fallback para permitir Easypanel si no se configuró explícitamente y estamos en prod
    # (Esto ayuda a diagnósticos rápidos si el usuario olvida configurar la ENV)
    pass
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(router)
app.include_router(test_router)
app.include_router(metrics_router)  # Sub-router para métricas
app.include_router(rag_router)      # Sub-router para RAG


# Para desarrollo/debugging
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )
