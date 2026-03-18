import asyncio
import json
import os
import socket
import uuid

from src.config.settings import settings
from src.events.emitter import event_emitter
from src.rag.processor import build_chunks, process_source
from src.rag.vector_store import insert_rows, upsert_chunks, upsert_metadata
from src.utils.logger import get_logger
from src.utils.redis_client import redis_client

logger = get_logger(__name__)

_worker_tasks: list[asyncio.Task] = []
_worker_stop: asyncio.Event | None = None
_consumer_base: str | None = None


async def _consume_loop(worker_idx: int) -> None:
    global _consumer_base
    if _consumer_base is None:
        host = socket.gethostname()
        _consumer_base = f"{host}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
    consumer = f"{_consumer_base}:{worker_idx}"
    stop = _worker_stop
    while True:
        if stop is not None and stop.is_set():
            return
        try:
            items = await redis_client.stream_read_group(
                settings.rag_ingest_stream_key,
                settings.rag_ingest_stream_group,
                consumer,
                count=1,
                block_ms=2000,
            )
        except Exception:
            await asyncio.sleep(0.5)
            continue

        if not items:
            continue
        try:
            stream_name, messages = items[0]
        except Exception:
            continue
        for message_id, fields in messages:
            payload_raw = None
            try:
                payload_raw = fields.get("payload")
            except Exception:
                payload_raw = None
            if not payload_raw:
                try:
                    await redis_client.stream_ack(
                        stream_name, settings.rag_ingest_stream_group, message_id
                    )
                except Exception:
                    pass
                continue

            try:
                payload = json.loads(payload_raw)
            except Exception:
                payload = {}

            try:
                processed = process_source(payload)
                empresa_id = str(processed.get("empresa_id") or "")
                doc_id = str(processed.get("doc_id") or "")
                mime = str(processed.get("mime") or "")
                tags = str(processed.get("tags") or "")
                title = doc_id
                exec_id = f"rag-{empresa_id}-{uuid.uuid4().hex[:8]}"
                await event_emitter.start_execution(exec_id, identifier=doc_id, user_name="rag_worker", chat_input="rag_ingest_job")

                text = processed.get("text") if isinstance(processed.get("text"), str) else None
                rows = processed.get("rows") if isinstance(processed.get("rows"), list) else None

                await event_emitter.emit_node_start("chunk_processor", exec_id)
                if isinstance(text, str) and text.strip():
                    chunks = build_chunks(text)
                    await event_emitter.emit_node_complete(
                        "chunk_processor",
                        exec_id,
                        output_preview=f"chunks={len(chunks)}"
                    )
                    await event_emitter.emit_node_start("embedding_model", exec_id)
                    upsert_chunks(empresa_id, doc_id, title, mime, tags, chunks)
                    await event_emitter.emit_node_complete(
                        "embedding_model",
                        exec_id,
                        output_preview=f"model={settings.embeddings_model} chunks={len(chunks)}"
                    )
                    await event_emitter.emit_node_start("vector_upsert", exec_id)
                    upsert_metadata(empresa_id, doc_id, title, None, None)
                    await event_emitter.emit_node_complete(
                        "vector_upsert",
                        exec_id,
                        output_preview=f"doc_id={doc_id} meta=upserted"
                    )
                elif isinstance(rows, list) and rows:
                    await event_emitter.emit_node_complete(
                        "chunk_processor",
                        exec_id,
                        output_preview=f"rows={len(rows)}"
                    )
                    await event_emitter.emit_node_skip("embedding_model", exec_id)
                    await event_emitter.emit_node_start("vector_upsert", exec_id)
                    insert_rows(empresa_id, doc_id, rows)
                    schema = ",".join(list(rows[0].keys())) if isinstance(rows[0], dict) else ""
                    upsert_metadata(empresa_id, doc_id, title, None, schema)
                    await event_emitter.emit_node_complete(
                        "vector_upsert",
                        exec_id,
                        output_preview=f"rows={len(rows)} schema_cols={(len(schema.split(',')) if schema else 0)}"
                    )
                else:
                    await event_emitter.emit_node_complete("chunk_processor", exec_id)
                    await event_emitter.emit_node_skip("embedding_model", exec_id)
                    await event_emitter.emit_node_start("vector_upsert", exec_id)
                    upsert_metadata(empresa_id, doc_id, title, None, None)
                    await event_emitter.emit_node_complete(
                        "vector_upsert",
                        exec_id,
                        output_preview=f"doc_id={doc_id} meta=upserted"
                    )

                await event_emitter.emit_node_start("rag_worker_core", exec_id)
                await event_emitter.emit_node_complete("rag_worker_core", exec_id)
                await event_emitter.complete_execution(exec_id)
            finally:
                try:
                    await redis_client.stream_ack(
                        stream_name, settings.rag_ingest_stream_group, message_id
                    )
                except Exception:
                    pass


async def start_rag_worker_pool() -> None:
    global _worker_stop, _worker_tasks
    if _worker_tasks:
        return
    if settings.execution_role not in {"all", "worker"}:
        return
    _worker_stop = asyncio.Event()
    try:
        await redis_client.stream_group_create(
            settings.rag_ingest_stream_key, settings.rag_ingest_stream_group
        )
    except Exception:
        pass
    n = max(1, int(settings.rag_ingest_worker_concurrency or 1))
    _worker_tasks = [asyncio.create_task(_consume_loop(i)) for i in range(n)]


async def stop_rag_worker_pool() -> None:
    global _worker_tasks, _worker_stop
    if _worker_stop is not None:
        _worker_stop.set()
    for t in list(_worker_tasks):
        try:
            t.cancel()
        except Exception:
            pass
    _worker_tasks = []
    _worker_stop = None


async def get_rag_queue_status() -> dict:
    stream_len = None
    consumers = None
    pending = None
    try:
        stream_len = await redis_client.stream_len(settings.rag_ingest_stream_key)
    except Exception:
        stream_len = None
    try:
        consumers = await redis_client.stream_info_consumers(
            settings.rag_ingest_stream_key, settings.rag_ingest_stream_group
        )
    except Exception:
        consumers = None
    try:
        pending = await redis_client.stream_pending_summary(
            settings.rag_ingest_stream_key, settings.rag_ingest_stream_group
        )
    except Exception:
        pending = None
    return {
        "stream": settings.rag_ingest_stream_key,
        "group": settings.rag_ingest_stream_group,
        "stream_len": stream_len,
        "consumers": consumers,
        "pending": pending,
        "worker_concurrency": settings.rag_ingest_worker_concurrency,
    }


if __name__ == "__main__":
    async def main():
        """Punto de entrada para el worker persistente."""
        logger.info("Iniciando Worker de RAG persistente")
        await start_rag_worker_pool()
        try:
            # Mantener el proceso vivo
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Deteniendo Worker de RAG...")
            await stop_rag_worker_pool()

    asyncio.run(main())
