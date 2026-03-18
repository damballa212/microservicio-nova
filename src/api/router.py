"""
Router de FastAPI.

Define los endpoints del chatbot:
- POST /webhook/inbound: Recibe webhooks de entrada
- GET /health: Health check
- GET /graph/diagram: Diagrama del grafo
"""

import hashlib
import json
import os
import re
import resource
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import PlainTextResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.adapters.dynamic_adapter import DynamicAdapter
from src.adapters.dynamic_adapter import _get_value as _da_get_value
from src.api.admin_router import router as admin_router
from src.api.credentials_router import credentials_router
from src.config.settings import settings
from src.events.emitter import event_emitter
from src.graph.builder import enqueue_chatbot, get_graph_diagram, get_queue_status, run_chatbot
from src.memory.episodes_worker import get_semantic_queue_status
from src.rag.vector_store import reranked_search
from src.utils.logger import get_logger
from src.utils.redis_client import redis_client
from src.utils.runtime_flags import is_sandbox_mode, set_sandbox_mode


logger = get_logger(__name__)

_IN_MEMORY_MAPPINGS: dict[str, dict[str, str]] = {}
router = APIRouter()
router.include_router(admin_router)
router.include_router(credentials_router)


DEFAULT_CANONICAL_FIELDS: list[str] = [
    "body.event",
    "body.conversation.messages[0].content",
    "body.conversation.messages[0].source_id",
    "body.conversation.messages[0].sender.name",
    "body.conversation.messages[0].sender.phone_number",
    "body.conversation.messages[0].sender.identifier",
    "body.conversation.messages[0].content_type",
    "body.conversation.messages[0].attachments",
    "body.conversation.messages[0].account_id",
    "body.conversation.messages[0].conversation_id",
    "body.conversation.contact_inbox.contact_id",
]


class SandboxRequest(BaseModel):
    enabled: bool = Field(default=True)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    queue = None
    try:
        queue = await get_queue_status()
    except Exception:
        queue = None
    return {
        "status": "healthy",
        "service": "chatbot-whatsapp",
        "version": "1.0.0",
        "queue": queue,
    }


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    Endpoint WebSocket para el Dashboard en tiempo real.
    Emite eventos de ejecución del grafo y logs.
    """
    await websocket.accept()
    await event_emitter.connect(websocket)
    try:
        while True:
            # Mantener conexión viva y escuchar mensajes (ping/pong implícito)
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_emitter.disconnect(websocket)
    except Exception as e:
        logger.error("Error en conexión WebSocket", error=str(e))
        event_emitter.disconnect(websocket)


def _normalize_inbound_payload(payload: Any) -> dict[str, Any]:
    def invalid() -> dict[str, Any]:
        return {"body": {"event": "invalid", "conversation": {"messages": []}}}

    if not isinstance(payload, dict):
        return invalid()

    p: dict[str, Any] = payload
    if "body" not in p:
        p = {"body": p}

    body_raw = p.get("body")
    if not isinstance(body_raw, dict):
        return invalid()

    body: dict[str, Any] = body_raw

    cw = body.get("chatwoot_payload")
    if isinstance(cw, dict):
        merged = dict(cw)
        for k in (
            "vertical_id",
            "empresa_id",
            "empresa_slug",
            "empresa_config",
            "agente_config",
            "memoria_conversacional",
            "rag_docs",
            "gating",
            "ia_state",
            "schema_version",
            "trace_id",
            "idempotency_key",
            "timestamp_received",
        ):
            if k in body and k not in merged:
                merged[k] = body.get(k)
        body = merged
        p["body"] = body

    if not isinstance(body.get("event"), str):
        ev = body.get("evento")
        if isinstance(ev, str):
            body["event"] = ev
        else:
            body["event"] = "invalid"

    def normalize_sender_type(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        v = value.strip()
        if not v:
            return ""
        if v.lower() == "contact":
            return "Contact"
        if v.lower() == "user":
            return "User"
        return v

    def build_message_from_raw(raw: dict[str, Any]) -> dict[str, Any]:
        account_id = raw.get("account_id")
        if not isinstance(account_id, int):
            acc = raw.get("account")
            if isinstance(acc, dict) and isinstance(acc.get("id"), int):
                account_id = acc.get("id")
            else:
                account_id = 0

        conversation_id = raw.get("conversation_id")
        if not isinstance(conversation_id, int):
            conv = raw.get("conversation")
            if isinstance(conv, dict) and isinstance(conv.get("id"), int):
                conversation_id = conv.get("id")
            else:
                conversation_id = 0

        sender = raw.get("sender")
        sender_obj: dict[str, Any] = sender if isinstance(sender, dict) else {}

        sender_type = normalize_sender_type(raw.get("sender_type"))
        if not sender_type:
            st = sender_obj.get("type")
            if isinstance(st, str) and st.lower() == "contact":
                sender_type = "Contact"
            elif isinstance(st, str) and st.lower() == "user":
                sender_type = "User"

        attachments = raw.get("attachments")
        attachments_list = attachments if isinstance(attachments, list) else []

        source_id = raw.get("source_id")
        if source_id is None:
            source_id = raw.get("id")

        return {
            "content": raw.get("content") if isinstance(raw.get("content"), str) else "",
            "account_id": account_id,
            "conversation_id": conversation_id,
            "source_id": source_id,
            "content_type": raw.get("content_type")
            if isinstance(raw.get("content_type"), str)
            else "text",
            "created_at": raw.get("created_at") if isinstance(raw.get("created_at"), str) else "",
            "sender_type": sender_type,
            "sender": sender_obj,
            "attachments": attachments_list,
        }

    conversation = body.get("conversation")
    conv_obj: dict[str, Any] = conversation if isinstance(conversation, dict) else {}
    msgs = conv_obj.get("messages")

    needs_message_build = not isinstance(msgs, list) or not msgs
    if needs_message_build and any(k in body for k in ("content", "sender", "message_type")):
        msg = build_message_from_raw(body)
        conv_obj = {**conv_obj, "messages": [msg]}
        body["conversation"] = conv_obj
        p["body"] = body
    elif not isinstance(msgs, list):
        conv_obj = {**conv_obj, "messages": []}
        body["conversation"] = conv_obj
        p["body"] = body

    return p


@router.post("/rag/ingest/upload")
async def rag_ingest_upload(
    file: UploadFile = File(...),
    empresa_id: int = Form(...),
    empresa_slug: str = Form(...),
    doc_id: str | None = Form(None),
    tags: str | None = Form(None),
):
    ct = file.content_type or ""
    allowed = set(settings.rag_allowed_mime_types or [])
    if ct not in allowed:
        raise HTTPException(status_code=400, detail="mime_not_allowed")
    data = await file.read()
    size = len(data)
    if size > int(settings.rag_upload_max_bytes or 0):
        raise HTTPException(status_code=400, detail="file_too_large")
    h = hashlib.sha256(data).hexdigest()
    did = doc_id or str(os.urandom(8).hex())
    base_dir = Path("data") / "rag" / "uploads" / str(empresa_id) / did
    base_dir.mkdir(parents=True, exist_ok=True)
    dest = base_dir / "file.bin"
    with open(dest, "wb") as f:
        f.write(data)
    ingest_id = str(os.urandom(16).hex())
    payload = {
        "ingest_id": ingest_id,
        "empresa_id": empresa_id,
        "empresa_slug": empresa_slug,
        "doc_id": did,
        "mime": ct,
        "size": size,
        "hash_sha256": h,
        "path": str(dest),
        "tags": tags,
        "source": "upload",
    }
    try:
        await redis_client.stream_group_create(
            settings.rag_ingest_stream_key, settings.rag_ingest_stream_group
        )
    except Exception:
        pass
    try:
        await redis_client.stream_add(
            settings.rag_ingest_stream_key,
            {"payload": json.dumps(payload, ensure_ascii=False)},
            maxlen=5000,
        )
    except Exception:
        pass
    return {"status": "received", "ingest_id": ingest_id, "doc_id": did}


@router.post("/rag/ingest/notify")
async def rag_ingest_notify(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")
    empresa_id = body.get("empresa_id")
    empresa_slug = body.get("empresa_slug")
    doc_id = body.get("doc_id")
    presigned_url = body.get("presigned_url")
    mime = body.get("mime")
    size = body.get("size")
    hash_sha256 = body.get("hash_sha256")
    if not isinstance(empresa_id, int) or not isinstance(empresa_slug, str):
        raise HTTPException(status_code=400, detail="invalid_tenant")
    if not isinstance(doc_id, str) or not doc_id:
        raise HTTPException(status_code=400, detail="invalid_doc_id")
    if not isinstance(presigned_url, str) or not presigned_url:
        raise HTTPException(status_code=400, detail="invalid_presigned_url")
    ingest_id = str(os.urandom(16).hex())
    payload = {
        "ingest_id": ingest_id,
        "empresa_id": empresa_id,
        "empresa_slug": empresa_slug,
        "doc_id": doc_id,
        "mime": mime,
        "size": size,
        "hash_sha256": hash_sha256,
        "presigned_url": presigned_url,
        "source": "notify",
    }
    try:
        await redis_client.stream_group_create(
            settings.rag_ingest_stream_key, settings.rag_ingest_stream_group
        )
    except Exception:
        pass
    try:
        await redis_client.stream_add(
            settings.rag_ingest_stream_key,
            {"payload": json.dumps(payload, ensure_ascii=False)},
            maxlen=5000,
        )
    except Exception:
        pass
    return {"status": "received", "ingest_id": ingest_id, "doc_id": doc_id}


class RagSearchRequest(BaseModel):
    empresa_id: int = Field(...)
    empresa_slug: str | None = Field(None)
    query: str = Field(...)
    top_k: int | None = Field(None)


@router.post("/rag/search")
async def rag_search(req: RagSearchRequest):
    q = req.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="empty_query")
    k = int(req.top_k or settings.rag_search_top_k or 10)
    docs = await reranked_search(str(req.empresa_id), q, k)
    return {"docs": docs[:k]}


async def _handle_inbound_payload(
    payload: Any, background_tasks: BackgroundTasks | None = None
) -> dict[str, Any]:
    logger.info(
        "Webhook recibido",
        event_type=(payload.get("body", payload) if isinstance(payload, dict) else {}).get(
            "event", "unknown"
        ),
    )
    p = _normalize_inbound_payload(payload)
    if settings.execution_queue_enabled:
        execution_id = await enqueue_chatbot(p)
        return {
            "status": "enqueued",
            "execution_id": execution_id,
        }
    if background_tasks is None:
        await run_chatbot(p)
    else:
        background_tasks.add_task(run_chatbot, p)
    return {
        "status": "received",
        "message": "Webhook procesándose en segundo plano",
    }


async def _handle_inbound_payload_sync(payload: Any) -> dict[str, Any]:
    logger.info(
        "Webhook sincrónico recibido",
        event_type=(payload.get("body", payload) if isinstance(payload, dict) else {}).get(
            "event", "unknown"
        ),
    )
    p = _normalize_inbound_payload(payload)
    result = await run_chatbot(p)
    return {
        "status": "processed",
        "should_continue": result.get("should_continue"),
        "error": result.get("error"),
        "ai_response": result.get("ai_response", "")[:200] if result.get("ai_response") else None,
    }


@router.post("/webhook/inbound")
async def inbound_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Recibe webhooks de entrada.
    Procesamiento en segundo plano para responder inmediatamente.
    """
    try:
        payload = await request.json()
        return await _handle_inbound_payload(payload, background_tasks=background_tasks)

    except Exception as e:
        logger.error("Error procesando webhook", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/inbound/sync")
async def inbound_webhook_sync(request: Request):
    """Webhook sincrónico para debugging."""
    try:
        payload = await request.json()
        return await _handle_inbound_payload_sync(payload)

    except Exception as e:
        logger.error("Error procesando webhook", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/chatwoot")
async def legacy_chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        return await _handle_inbound_payload(payload, background_tasks=background_tasks)
    except Exception as e:
        logger.error("Error procesando webhook", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/chatwoot/sync")
async def legacy_chatwoot_webhook_sync(request: Request):
    try:
        payload = await request.json()
        return await _handle_inbound_payload_sync(payload)
    except Exception as e:
        logger.error("Error procesando webhook", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/status")
async def neural_status():
    q = None
    try:
        q = await get_queue_status()
    except Exception:
        q = None
    load = None
    try:
        load = os.getloadavg()
    except Exception:
        load = None
    rss = None
    cpu = None
    try:
        ru = resource.getrusage(resource.RUSAGE_SELF)
        rss = ru.ru_maxrss
        cpu = {"user_s": ru.ru_utime, "system_s": ru.ru_stime}
    except Exception:
        rss = None
        cpu = None
    return {
        "dashboard_connections": len(event_emitter.connections),
        "active_executions": len(event_emitter.executions),
        "queue": q,
        "loadavg": load,
        "process": {"rss": rss, "cpu": cpu},
    }


@router.get("/semantic/status")
async def semantic_status():
    s = None
    try:
        s = await get_semantic_queue_status()
    except Exception:
        s = None
    return {"semantic_queue": s}


@router.get("/graph/diagram", response_class=PlainTextResponse)
async def graph_diagram():
    """Retorna el diagrama Mermaid del grafo."""
    return get_graph_diagram()


@router.get("/executions/history")
async def execution_history():
    """Retorna el historial de ejecuciones recientes."""
    items: list[dict] = []
    try:
        raw = await redis_client.get_list("metrics:executions")
        if raw:
            import json as _json

            parsed = []
            for s in raw[-settings.metrics_history_max_items :]:
                try:
                    parsed.append(_json.loads(s))
                except Exception:
                    pass
            items = list(reversed(parsed[-20:]))
    except Exception:
        items = []
    if not items:
        items = [e.model_dump(mode="json") for e in event_emitter.execution_history[-20:]]
    return {
        "executions": items,
        "active": [e.model_dump(mode="json") for e in event_emitter.executions.values()],
    }


@router.get("/logs/history")
async def logs_history():
    return {"logs": event_emitter.logs_history[-200:]}


@router.get("/logs/execution/{execution_id}")
async def logs_execution(execution_id: str):
    try:
        v = await redis_client.get_value(f"metrics:logs:{execution_id}")
        if v:
            import json as _json

            return {"execution_id": execution_id, "logs": _json.loads(v)}
    except Exception:
        pass
    for e in event_emitter.execution_history:
        if e.execution_id == execution_id:
            return {"execution_id": execution_id, "logs": e.logs}
    evt = event_emitter.executions.get(execution_id)
    if evt:
        return {"execution_id": execution_id, "logs": evt.logs}
    raise HTTPException(status_code=404, detail="Execution not found")


@router.get("/metrics/summary")
async def metrics_summary():
    hist_items: list[dict] = []
    try:
        raw = await redis_client.get_list("metrics:executions")
        if raw:
            import json as _json

            for s in raw[-settings.metrics_history_max_items :]:
                try:
                    hist_items.append(_json.loads(s))
                except Exception:
                    pass
            hist_items = hist_items[-100:]
    except Exception:
        hist_items = []
    if not hist_items:
        hist_items = [e.model_dump(mode="json") for e in event_emitter.execution_history[-100:]]
    total_exec = len(hist_items)
    input_tokens_sum = sum([(e.get("input_tokens_total") or 0) for e in hist_items])
    output_tokens_sum = sum([(e.get("output_tokens_total") or 0) for e in hist_items])
    total_tokens_sum = sum(
        [
            (
                e.get("total_tokens_total")
                or ((e.get("input_tokens_total") or 0) + (e.get("output_tokens_total") or 0))
            )
            for e in hist_items
        ]
    )
    cost_sum = sum([(e.get("cost_usd_total") or 0.0) for e in hist_items])
    avg_input = input_tokens_sum / total_exec if total_exec else 0
    avg_output = output_tokens_sum / total_exec if total_exec else 0
    avg_total = total_tokens_sum / total_exec if total_exec else 0
    avg_cost = cost_sum / total_exec if total_exec else 0.0
    per_node = {}
    for e in hist_items:
        for name, n in (e.get("nodes") or {}).items():
            d = per_node.setdefault(
                name,
                {
                    "count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "errors": 0,
                    "duration_ms": 0.0,
                },
            )
            d["count"] += 1
            d["input_tokens"] += n.get("input_tokens") or 0
            d["output_tokens"] += n.get("output_tokens") or 0
            d["total_tokens"] += n.get("total_tokens") or 0
            d["duration_ms"] += n.get("duration_ms") or 0.0
            if n.get("status") == "error":
                d["errors"] += 1
    for name, d in per_node.items():
        c = d["count"] or 1
        d["avg_input_tokens"] = d["input_tokens"] / c
        d["avg_output_tokens"] = d["output_tokens"] / c
        d["avg_total_tokens"] = d["total_tokens"] / c
        d["avg_duration_ms"] = d["duration_ms"] / c
    return {
        "executions": total_exec,
        "totals": {
            "input_tokens": input_tokens_sum,
            "output_tokens": output_tokens_sum,
            "total_tokens": total_tokens_sum,
            "cost_usd": cost_sum,
        },
        "averages": {
            "input_tokens": avg_input,
            "output_tokens": avg_output,
            "total_tokens": avg_total,
            "cost_usd": avg_cost,
        },
        "per_node": per_node,
    }


@router.get("/metrics/execution/{execution_id}")
async def metrics_execution(execution_id: str):
    try:
        v = await redis_client.get_value(f"metrics:execution:{execution_id}")
        if v:
            import json as _json

            return _json.loads(v)
    except Exception:
        pass
    for e in event_emitter.execution_history:
        if e.execution_id == execution_id:
            return e.model_dump(mode="json")
    for e in event_emitter.executions.values():
        if e.execution_id == execution_id:
            return e.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Execution not found")


@router.get("/metrics/node/{node_name}")
async def metrics_node(node_name: str):
    items: list[dict] = []
    try:
        raw = await redis_client.get_list("metrics:executions")
        if raw:
            import json as _json

            for s in raw[-settings.metrics_history_max_items :]:
                try:
                    e = _json.loads(s)
                    n = (e.get("nodes") or {}).get(node_name)
                    if n:
                        items.append(n)
                except Exception:
                    pass
    except Exception:
        pass
    if not items:
        for e in event_emitter.execution_history[-200:]:
            n = e.nodes.get(node_name)
            if n:
                items.append(n.model_dump(mode="json"))
    return {"node": node_name, "items": items}


@router.post("/config/sandbox")
async def set_sandbox(req: SandboxRequest):
    set_sandbox_mode(req.enabled)
    return {"status": "ok", "sandbox_mode": is_sandbox_mode()}


@router.get("/config/sandbox")
async def get_sandbox():
    return {"sandbox_mode": is_sandbox_mode()}


@router.get("/metrics/trends")
async def metrics_trends():
    hist_items: list[dict] = []
    try:
        raw = await redis_client.get_list("metrics:executions")
        if raw:
            import json as _json

            for s in raw[-settings.metrics_history_max_items :]:
                try:
                    hist_items.append(_json.loads(s))
                except Exception:
                    pass
            hist_items = hist_items[-100:]
    except Exception:
        hist_items = []
    if not hist_items:
        hist_items = [e.model_dump(mode="json") for e in event_emitter.execution_history[-100:]]
    series = []
    for e in hist_items:
        total_tokens = e.get("total_tokens_total") or (
            (e.get("input_tokens_total") or 0) + (e.get("output_tokens_total") or 0)
        )
        duration_ms = None
        if e.get("started_at") and e.get("completed_at"):
            try:
                from datetime import datetime as _dt

                s = _dt.fromisoformat(e["started_at"])
                c = _dt.fromisoformat(e["completed_at"])
                duration_ms = (c - s).total_seconds() * 1000
            except Exception:
                duration_ms = None
        series.append(
            {
                "timestamp": e.get("started_at"),
                "execution_id": e.get("execution_id"),
                "total_tokens": total_tokens,
                "input_tokens": e.get("input_tokens_total") or 0,
                "output_tokens": e.get("output_tokens_total") or 0,
                "duration_ms": duration_ms,
                "cost_usd": e.get("cost_usd_total") or 0.0,
                "status": (
                    e.get("status") if isinstance(e.get("status"), str) else str(e.get("status"))
                ),
            }
        )
    return {"series": series}


@router.delete("/metrics/reset")
async def metrics_reset():
    try:
        await redis_client.delete_key("metrics:executions")
    except Exception:
        pass
    return {"status": "ok"}


@router.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "service": "Chatbot WhatsApp con LangGraph",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "diagram": "/graph/diagram",
    }


class MappingPreviewRequest(BaseModel):
    source_name: str = Field(min_length=1)
    sample_payload: dict[str, Any]
    mapping: dict[str, str]


class SaveMappingRequest(BaseModel):
    source_name: str = Field(min_length=1)
    mapping: dict[str, str]


class GenerateMappingRequest(BaseModel):
    source_name: str = Field(min_length=1)
    sample_payload: dict[str, Any]
    canonical_fields: list[str] | None = None


def _iter_paths(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    results: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            results.extend(_iter_paths(v, new_prefix))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            new_prefix = f"{prefix}[{i}]" if prefix else f"[{i}]"
            results.extend(_iter_paths(v, new_prefix))
    else:
        results.append((prefix, data))
    return results


def _heuristic_generate_mapping(
    sample: dict[str, Any], canonical_fields: list[str]
) -> dict[str, str]:
    paths = _iter_paths(sample)
    by_key: dict[str, list[tuple[str, Any]]] = {}
    for p, v in paths:
        last = p.split(".")[-1].replace("[", ".").replace("]", "").split(".")[-1]
        by_key.setdefault(last.lower(), []).append((p, v))
    syn: dict[str, list[str]] = {
        "body.event": ["event", "type", "action"],
        "body.conversation.messages[0].content": [
            "text",
            "message",
            "content",
            "body",
            "msg",
            "mensaje",
        ],
        "body.conversation.messages[0].source_id": ["id", "message_id", "uuid", "source_id"],
        "body.conversation.messages[0].sender.name": ["name", "full_name", "fullname", "from_name"],
        "body.conversation.messages[0].sender.phone_number": [
            "phone",
            "phone_number",
            "msisdn",
            "telefono",
            "wa_id",
            "whatsapp",
        ],
        "body.conversation.messages[0].sender.identifier": [
            "identifier",
            "wa_id",
            "whatsapp_id",
            "whatsapp",
            "phone",
            "phone_number",
            "msisdn",
        ],
        "body.conversation.messages[0].content_type": ["type", "content_type", "mime", "kind"],
        "body.conversation.messages[0].attachments": [
            "attachments",
            "files",
            "media",
            "images",
            "audios",
            "documents",
        ],
        "body.conversation.messages[0].account_id": ["account", "account_id", "acct_id"],
        "body.conversation.messages[0].conversation_id": [
            "conversation",
            "conversation_id",
            "thread_id",
            "chat_id",
        ],
        "body.conversation.contact_inbox.contact_id": [
            "contact",
            "contact_id",
            "user_id",
            "customer_id",
        ],
    }
    mapping: dict[str, str] = {}
    for field in canonical_fields:
        candidates = syn.get(field, [])
        chosen: str | None = None
        for c in candidates:
            if c in by_key:
                for p, v in by_key[c]:
                    if field.endswith("attachments") and isinstance(v, list):
                        chosen = p
                        break
                    if (
                        field.endswith("account_id")
                        or field.endswith("conversation_id")
                        or field.endswith("contact_id")
                    ):
                        if isinstance(v, int):
                            chosen = p
                            break
                    if field.endswith("content_type") and isinstance(v, str):
                        chosen = p
                        break
                    if field.endswith("phone_number") and isinstance(v, str):
                        chosen = p
                        break
                    if field.endswith("name") and isinstance(v, str):
                        chosen = p
                        break
                    if field.endswith("source_id") and isinstance(v, (str, int)):
                        chosen = p
                        break
                    if field.endswith("content") and isinstance(v, str):
                        chosen = p
                        break
                    if field.endswith("event") and isinstance(v, str):
                        chosen = p
                        break
            if chosen:
                break
        if chosen:
            mapping[field] = chosen
    return mapping


def _try_parse_json(text: str) -> dict[str, Any] | None:
    t = text.strip()
    try:
        val = json.loads(t)
        return val if isinstance(val, dict) else None
    except Exception:
        m = re.search(r"\{[\s\S]*\}", t)
        if m:
            try:
                val2 = json.loads(m.group(0))
                return val2 if isinstance(val2, dict) else None
            except Exception:
                return None
    return None


@router.post("/onboarding/normalize-preview")
async def normalize_preview(req: MappingPreviewRequest):
    adapter = DynamicAdapter(req.mapping)
    transformed = adapter.transform(req.sample_payload)
    transformed = DynamicAdapter.apply_defaults(transformed)
    missing = adapter.validate(req.sample_payload)
    return {"preview": transformed, "missing": missing}


@router.post("/onboarding/generate-mapping")
async def generate_mapping(req: GenerateMappingRequest):
    canonical = req.canonical_fields or DEFAULT_CANONICAL_FIELDS
    suggested: dict[str, str] = {}
    used_ai = False
    try:
        if settings.openai_api_key:
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
                if settings.openai_base_url != "https://api.openai.com/v1"
                else None,
            )
            messages: Any = [
                {
                    "role": "system",
                    "content": "Devuelve solo JSON con un objeto {canonical_field: source_path}. Usa notación de puntos y [i] para arrays. Incluye solo campos con valor presente en el payload. No añadas texto fuera del JSON.",
                },
                {
                    "role": "user",
                    "content": "Payload de origen:\n"
                    + json.dumps(req.sample_payload, ensure_ascii=False)
                    + "\n\nCampos canónicos:\n"
                    + "\n".join(canonical),
                },
            ]
            completion = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0,
            )
            text = completion.choices[0].message.content or ""
            parsed = _try_parse_json(text)
            if isinstance(parsed, dict):
                suggested = {
                    str(k): str(v)
                    for k, v in parsed.items()
                    if isinstance(k, str) and isinstance(v, str)
                }
                used_ai = True
        elif settings.google_api_key:
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.google_api_key,
                temperature=0,
            )
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "Devuelve solo JSON con un objeto {{canonical_field: source_path}}. Usa notación de puntos y [i] para arrays. Incluye solo campos con valor presente en el payload. No añadas texto fuera del JSON.",
                    ),
                    ("human", "Payload de origen:\n{source}\n\nCampos canónicos:\n{fields}"),
                ]
            )
            chain = prompt | llm
            resp = await chain.ainvoke(
                {
                    "source": json.dumps(req.sample_payload, ensure_ascii=False),
                    "fields": "\n".join(canonical),
                }
            )
            raw_text = resp.content if hasattr(resp, "content") else str(resp)
            raw_text = raw_text if isinstance(raw_text, str) else str(raw_text)
            parsed = _try_parse_json(raw_text)
            if isinstance(parsed, dict):
                suggested = {
                    str(k): str(v)
                    for k, v in parsed.items()
                    if isinstance(k, str) and isinstance(v, str)
                }
                used_ai = True
    except Exception as e:
        logger.warning("Fallo IA para generar mapeo", error=str(e))
    if not suggested:
        suggested = _heuristic_generate_mapping(req.sample_payload, canonical)
    else:
        # Completar campos faltantes o inválidos con heurísticas y validación de tipos
        heur = _heuristic_generate_mapping(req.sample_payload, canonical)
        # Detectar campos inválidos (paths que no existen en el sample)
        adapter_tmp = DynamicAdapter(suggested)
        invalid = set(adapter_tmp.validate(req.sample_payload))

        # Validación de tipo esperado por campo canónico
        def expected_type(field: str):
            if field.endswith("attachments"):
                return list
            if (
                field.endswith("account_id")
                or field.endswith("conversation_id")
                or field.endswith("contact_id")
            ):
                return int
            if field.endswith("source_id"):
                return (str, int)
            return str

        for k, src in list(suggested.items()):
            try:
                val = _da_get_value(req.sample_payload, src)
            except Exception:
                val = None
            exp = expected_type(k)
            if val is None or (not isinstance(val, exp)):
                invalid.add(k)
        # Si event es inválido, removemos para que se aplique el default
        if "body.event" in invalid:
            suggested.pop("body.event", None)
        for k, v in heur.items():
            if k not in suggested or k in invalid:
                suggested[k] = v
    adapter = DynamicAdapter(suggested)
    preview = adapter.transform(req.sample_payload)
    preview = DynamicAdapter.apply_defaults(preview)
    missing_values = adapter.validate(req.sample_payload)
    missing = list(sorted(set(missing_values + [f for f in canonical if f not in suggested])))
    return {"suggested": suggested, "preview": preview, "missing": missing, "used_ai": used_ai}


@router.post("/onboarding/mapping")
async def save_mapping(req: SaveMappingRequest):
    key = f"crm:mapping:{req.source_name}"
    _IN_MEMORY_MAPPINGS[req.source_name] = req.mapping
    try:
        client = await redis_client.get_client()
        await client.set(key, json.dumps(req.mapping))
    except Exception:
        pass
    return {"status": "saved", "source_name": req.source_name}


@router.get("/onboarding/mapping/{source_name}")
async def get_mapping(source_name: str):
    key = f"crm:mapping:{source_name}"
    if source_name in _IN_MEMORY_MAPPINGS:
        return {"source_name": source_name, "mapping": _IN_MEMORY_MAPPINGS[source_name]}
    try:
        client = await redis_client.get_client()
        raw = await client.get(key)
        if raw is not None:
            return {"source_name": source_name, "mapping": json.loads(raw)}
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Mapping not found")


@router.post("/webhook/generic/{source_name}")
async def generic_webhook(source_name: str, request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        key = f"crm:mapping:{source_name}"
        mapping: dict[str, str] | None = None
        try:
            client = await redis_client.get_client()
            raw = await client.get(key)
            if raw is not None:
                mapping = json.loads(raw)
        except Exception:
            mapping = _IN_MEMORY_MAPPINGS.get(source_name)
        if mapping is None:
            raise HTTPException(status_code=404, detail="Mapping not configured")
        adapter = DynamicAdapter(mapping)
        normalized = adapter.transform(payload)
        normalized = DynamicAdapter.apply_defaults(normalized)
        if settings.execution_queue_enabled:
            execution_id = await enqueue_chatbot(normalized)
            return {"status": "enqueued", "source": source_name, "execution_id": execution_id}
        background_tasks.add_task(run_chatbot, normalized)
        return {"status": "received", "source": source_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error procesando webhook genérico", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/generic/{source_name}/sync")
async def generic_webhook_sync(source_name: str, request: Request):
    try:
        payload = await request.json()
        key = f"crm:mapping:{source_name}"
        mapping: dict[str, str] | None = None
        try:
            client = await redis_client.get_client()
            raw = await client.get(key)
            if raw is not None:
                mapping = json.loads(raw)
        except Exception:
            mapping = _IN_MEMORY_MAPPINGS.get(source_name)
        if mapping is None:
            raise HTTPException(status_code=404, detail="Mapping not configured")
        adapter = DynamicAdapter(mapping)
        normalized = adapter.transform(payload)
        normalized = DynamicAdapter.apply_defaults(normalized)
        result = await run_chatbot(normalized)
        return {
            "status": "processed",
            "should_continue": result.get("should_continue"),
            "error": result.get("error"),
            "ai_response": result.get("ai_response", "")[:200]
            if result.get("ai_response")
            else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error procesando webhook genérico", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
