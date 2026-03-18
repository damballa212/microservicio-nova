import json
import uuid
from typing import Any

from src.config.settings import settings
from src.events.emitter import event_emitter
from src.integrations.outbound_webhook import outbound_webhook_client
from src.models.state import ChatbotState
from src.utils.logger import get_logger
from src.utils.runtime_flags import is_sandbox_mode

logger = get_logger(__name__)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            return int(value)
    except Exception:
        pass
    return default


async def post_to_outbound_webhook(state: ChatbotState) -> ChatbotState:
    tenant_id = _safe_int(state.get("tenant_id"), default=state.get("account_id", 0))
    tenant_slug = state.get("tenant_slug") or None
    user_name = state.get("user_name", "")
    phone_number = state.get("phone_number", "")
    ai_response = state.get("ai_response", "")
    conversation_id = state.get("conversation_id", 0)
    current = state.get("current_message", {})

    raw = state.get("raw_payload", {})
    body = raw.get("body", raw)
    email = None
    try:
        sender = (body.get("conversation", {}).get("messages", [{}]) or [{}])[0].get("sender", {})
        em = sender.get("email")
        if isinstance(em, str) and em:
            email = em
    except Exception:
        email = None

    account_id = _safe_int(state.get("account_id"), 0)
    source_id = None
    try:
        if isinstance(current, dict):
            sid = current.get("source_id") or current.get("id")
            if isinstance(sid, (str, int)):
                source_id = str(sid)
        if not source_id:
            msg0 = (body.get("conversation", {}).get("messages", [{}]) or [{}])[0]
            sid2 = msg0.get("source_id") or msg0.get("id")
            if isinstance(sid2, (str, int)):
                source_id = str(sid2)
    except Exception:
        source_id = None

    trace_id = state.get("_trace_id") or state.get("_execution_id") or str(uuid.uuid4())
    timestamp_received = None
    try:
        ts_in = body.get("timestamp_received")
        if isinstance(ts_in, str) and ts_in:
            timestamp_received = ts_in
        else:
            ts = current.get("created_at")
            if isinstance(ts, str) and ts:
                timestamp_received = ts
    except Exception:
        timestamp_received = None

    idempotency_key = None
    try:
        idem_in = body.get("idempotency_key")
        if isinstance(idem_in, str) and idem_in:
            idempotency_key = idem_in
        elif account_id and conversation_id and source_id:
            idempotency_key = f"msg:{account_id}:{conversation_id}:{source_id}"
    except Exception:
        idempotency_key = None

    execution_id = state.get("_execution_id") or ""
    observability: dict[str, Any] | None = None
    try:
        if execution_id:
            evt = event_emitter.executions.get(execution_id)
            ne = evt.nodes.get("generate_response") if evt else None
            if ne:
                observability = {
                    "provider": ne.provider,
                    "model": ne.model_id,
                    "tokens_in": ne.input_tokens,
                    "tokens_out": ne.output_tokens,
                    "total_tokens": ne.total_tokens,
                    "latency_ms": ne.duration_ms,
                    "cost_usd": ne.cost_usd,
                }
    except Exception:
        observability = None

    needs_escalation = bool(
        state.get("needs_escalation", False) or state.get("gating_escalate", False)
    )
    escalation_reason = state.get("escalation_reason")
    if not isinstance(escalation_reason, str) or not escalation_reason:
        escalation_reason = None

    actions = state.get("actions")
    actions_payload = actions if isinstance(actions, dict) else None

    etiquetas_aplicadas: list[str] = []
    if isinstance(actions_payload, dict):
        raw_labels = actions_payload.get("apply_labels")
        if isinstance(raw_labels, list):
            etiquetas_aplicadas = [x for x in raw_labels if isinstance(x, str)]

    lead_calificado = False
    if isinstance(actions_payload, dict):
        raw_lead = actions_payload.get("lead_calificado")
        if raw_lead is None:
            raw_lead = actions_payload.get("lead_qualified")
        try:
            lead_calificado = bool(raw_lead)
        except Exception:
            lead_calificado = False

    intencion_detectada = None
    if isinstance(actions_payload, dict):
        raw_intent = actions_payload.get("intencion_detectada")
        if raw_intent is None:
            raw_intent = actions_payload.get("intent")
        if isinstance(raw_intent, str) and raw_intent:
            intencion_detectada = raw_intent

    formatted_parts = state.get("formatted_parts", [])
    reply_parts: list[str] | None = None
    if isinstance(formatted_parts, list):
        reply_parts = [p for p in formatted_parts if isinstance(p, str)] or None

    payload = {
        "schema_version": "1.0",
        "trace_id": trace_id,
        "idempotency_key": idempotency_key,
        "timestamp_received": timestamp_received,
        "tenant_id": tenant_id,
        "tenant_slug": tenant_slug,
        "agent": "NOVA",
        "event": "message_processed",
        "contact": {
            "name": user_name or None,
            "phone": phone_number or None,
            "email": email,
        },
        "conversation_id": conversation_id or None,
        "message": {
            "text": current.get("content") or "",
            "message_id": source_id,
        },
        "agent_reply": {
            "text": ai_response or "",
            "parts": reply_parts,
        },
        "signals": {
            "needs_human": needs_escalation,
            "reason": escalation_reason,
        },
        "actions": actions_payload,
        "metadata": {
            "source": "nova",
            "execution_id": state.get("_execution_id") or "",
            "gating": {
                "stop": bool(state.get("gating_stop")),
                "escalate": bool(state.get("gating_escalate")),
                "bot_state": state.get("bot_state") or None,
            },
            "rag": {
                "docs_count": len(state.get("rag_docs") or [])
                if isinstance(state.get("rag_docs"), list)
                else 0,
            },
            "sheets": {
                "google_sheet_id": state.get("google_sheet_id") or None,
                "inventory_query": state.get("inventory_query"),
                "has_result": bool(state.get("sheets_result")),
            },
        },
        "observability": observability,
        "empresa_id": tenant_id,
        "empresa_slug": tenant_slug,
        "agente": "NOVA",
        "evento": "message_processed",
        "contacto": {
            "nombre": user_name or None,
            "telefono": phone_number or None,
            "email": email,
        },
        "conversacion_id": conversation_id or None,
        "mensaje": {
            "texto": current.get("content") or "",
            "message_id": source_id,
        },
        "respuesta_agente": {
            "texto": ai_response or "",
            "partes": reply_parts,
        },
        "acciones": actions_payload,
        "intencion_detectada": intencion_detectada,
        "etiquetas_aplicadas": etiquetas_aplicadas,
        "lead_calificado": lead_calificado,
        "escalate_to_human": needs_escalation,
    }

    try:
        logger.info(
            "Enviando webhook outbound", tenant_id=tenant_id, conversation_id=conversation_id
        )
        try:
            preview_out = json.dumps(payload, ensure_ascii=False)[:500]
            if execution_id:
                await event_emitter.update_payload_out_preview(execution_id, preview_out)
        except Exception:
            pass
        if (
            not settings.outbound_webhook_base_url
            or state.get("_sandbox_mode")
            or is_sandbox_mode()
        ):
            result = {"status_code": 0, "data": {"skipped": True}}
        else:
            result = await outbound_webhook_client.send(payload)
        state["_outbound_response"] = result
        logger.info("Webhook outbound enviado", status_code=result.get("status_code"))
    except Exception as e:
        logger.error("Error enviando outbound webhook", error=str(e))
        state["error"] = f"Error posting outbound webhook: {str(e)}"

    return state
