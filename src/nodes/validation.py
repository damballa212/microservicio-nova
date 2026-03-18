"""
Nodos de validación.

Implementa las fases 1-4 del workflow de n8n:
1. validate_event: Verifica que sea "message_created"
2. validate_sender: Verifica que sea un contacto (no agente)
3. check_bot_state: Verifica que el bot esté activo
4. extract_message_data: Extrae datos del webhook

REFACTORIZACIÓN: Lógica común de extracción centralizada en _extract_common_fields()
"""

from typing import Any, Literal

from src.config.settings import settings
from src.models.state import ChatbotState
from src.utils.logger import get_logger

logger = get_logger(__name__)


# === HELPER CENTRALIZADO ===

def _extract_common_fields(body: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    """
    Extrae campos comunes del payload que se usan en múltiples nodos.
    
    Centraliza la lógica duplicada entre check_bot_state y extract_message_data.
    
    Returns:
        Diccionario con campos extraídos
    """
    conversation = body.get("conversation", {})
    sender = message.get("sender", {})
    contact_inbox = conversation.get("contact_inbox", {})
    
    # Extraer identifier
    identifier = sender.get("identifier", "") or ""
    phone_number = sender.get("phone_number", "") or ""
    if not identifier and phone_number:
        cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        identifier = f"whatsapp:{cleaned}"
    
    # Extraer source_id
    src_id = message.get("source_id")
    if src_id is None:
        src_id = message.get("id")
    try:
        src_id_str = "" if src_id is None else str(src_id)
    except Exception:
        src_id_str = ""
    
    # Tenant info
    tenant_id = body.get("empresa_id")
    if tenant_id is None:
        tenant_id = message.get("account_id")
    tenant_slug = body.get("empresa_slug") or ""
    
    try:
        tenant_id_str = str(tenant_id) if tenant_id is not None else ""
    except Exception:
        tenant_id_str = ""
    
    tenant_slug_str = str(tenant_slug) if isinstance(tenant_slug, str) else ""
    
    # Namespacing
    base_id = identifier
    namespaced_id = base_id
    if settings and getattr(settings, "namespace_by_tenant", False):
        ns = tenant_slug_str or tenant_id_str
        namespaced_id = f"{ns}:{base_id}" if ns else base_id
    
    # Trace ID
    trace_id = body.get("trace_id")
    trace_id_str = trace_id if isinstance(trace_id, str) and trace_id else None
    
    return {
        "identifier": identifier,
        "phone_number": phone_number,
        "user_name": sender.get("name", ""),
        "account_id": message.get("account_id", 0),
        "conversation_id": message.get("conversation_id", 0),
        "contact_id": contact_inbox.get("contact_id", 0),
        "current_message": {
            "content": message.get("content", ""),
            "content_type": message.get("content_type", "text"),
            "source_id": src_id_str,
            "created_at": message.get("created_at", ""),
            "attachments": message.get("attachments", []),
        },
        "tenant_id": tenant_id_str,
        "tenant_slug": tenant_slug_str,
        "namespaced_id": namespaced_id,
        "_trace_id": trace_id_str,
    }


def _parse_ia_state(value: object) -> bool | None:
    """Parsea el estado de IA desde varios formatos posibles."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"on", "true", "1", "yes", "si", "sí", "activo", "enabled", "enable"}:
            return True
        if v in {"off", "false", "0", "no", "inactivo", "disabled", "disable"}:
            return False
    return None


def _extract_gating_flags(body: dict[str, Any], existing_stop: bool = False, existing_escalate: bool = False) -> tuple[bool, bool]:
    """Extrae los flags de gating del payload."""
    gating = body.get("gating") or {}
    
    try:
        gating_stop = bool(existing_stop or gating.get("stop") or gating.get("stop_processing"))
    except Exception:
        gating_stop = bool(existing_stop)
    
    try:
        gating_escalate = bool(existing_escalate or gating.get("escalate") or gating.get("force_escalation"))
    except Exception:
        gating_escalate = bool(existing_escalate)
    
    return gating_stop, gating_escalate


# === NODOS DE VALIDACIÓN ===

def validate_event(state: ChatbotState) -> ChatbotState:
    """
    Nodo 1: Valida que el evento sea 'message_created'.

    Corresponde al nodo 'If2' del workflow de n8n.
    Solo procesa eventos de nuevos mensajes.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con event_type y should_continue actualizados
    """
    payload = state.get("raw_payload", {})
    body = payload.get("body", payload)
    event = body.get("event", "")

    state["event_type"] = event
    state["should_continue"] = event == "message_created"

    if not state["should_continue"]:
        logger.debug("Evento ignorado (no es message_created)", event_type=event)
    else:
        logger.debug("Evento válido", event_type=event)

    return state


def route_after_event_validation(state: ChatbotState) -> Literal["continue", "stop"]:
    """Routing después de validar el evento."""
    return "continue" if state.get("should_continue", False) else "stop"


def validate_sender(state: ChatbotState) -> ChatbotState:
    """
    Nodo 2: Valida que el mensaje sea de un contacto (no agente).

    Corresponde al nodo 'If3' del workflow de n8n.
    Ignora mensajes enviados por agentes humanos.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con sender_type y should_continue actualizados
    """
    payload = state.get("raw_payload", {})
    body = payload.get("body", payload)
    conversation = body.get("conversation", {})
    messages = conversation.get("messages", [])

    if not messages:
        state["sender_type"] = ""
        state["should_continue"] = False
        logger.warning("No se encontraron mensajes en el payload")
        return state

    message = messages[0]
    sender_type = message.get("sender_type", "")

    state["sender_type"] = sender_type
    state["should_continue"] = sender_type == "Contact"

    if not state["should_continue"]:
        logger.debug("Mensaje de agente ignorado", sender_type=sender_type)
    else:
        logger.debug("Mensaje de contacto válido")

    return state


def route_after_sender_validation(state: ChatbotState) -> Literal["continue", "stop"]:
    """Routing después de validar el sender."""
    return "continue" if state.get("should_continue", False) else "stop"


def check_bot_state(state: ChatbotState) -> ChatbotState:
    """
    Nodo 3: Verifica que el bot esté activo para este usuario.

    Corresponde al nodo 'If6' del workflow de n8n.
    Si el estado del bot es 'OFF', no procesa el mensaje.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con bot_state y should_continue actualizados
    """
    payload = state.get("raw_payload", {})
    body = payload.get("body", payload)
    conversation = body.get("conversation", {})
    messages = conversation.get("messages", [])

    if not messages:
        state["bot_state"] = "ON"
        state["should_continue"] = False
        return state

    message = messages[0]
    sender = message.get("sender", {})
    custom_attributes = sender.get("custom_attributes", {})
    conv_custom = conversation.get("custom_attributes", {})

    # Usar helper centralizado para campos comunes
    common_fields = _extract_common_fields(body, message)
    state["identifier"] = common_fields["identifier"]
    state["phone_number"] = common_fields["phone_number"]
    state["user_name"] = common_fields["user_name"]
    state["account_id"] = common_fields["account_id"]
    state["conversation_id"] = common_fields["conversation_id"]
    state["contact_id"] = common_fields["contact_id"]
    state["current_message"] = common_fields["current_message"]
    state["tenant_id"] = common_fields["tenant_id"]
    state["tenant_slug"] = common_fields["tenant_slug"]
    state["namespaced_id"] = common_fields["namespaced_id"]
    if common_fields["_trace_id"]:
        state["_trace_id"] = common_fields["_trace_id"]

    # Extraer gating flags
    existing_stop = bool(state.get("gating_stop"))
    existing_escalate = bool(state.get("gating_escalate"))
    gating_stop, gating_escalate = _extract_gating_flags(body, existing_stop, existing_escalate)
    state["gating_stop"] = gating_stop
    state["gating_escalate"] = gating_escalate

    # Determinar estado del bot
    ia_enabled = _parse_ia_state(body.get("ia_state"))
    bot_state = custom_attributes.get("estado", "ON")
    
    bs2 = conv_custom.get("bot_status")
    if isinstance(bs2, str) and bs2:
        bot_state = bs2

    if ia_enabled is False:
        bot_state = "OFF"
        state["gating_stop"] = True
    elif ia_enabled is True:
        bot_state = "ON"

    state["bot_state"] = bot_state
    
    if state.get("gating_stop"):
        state["should_continue"] = False
    else:
        state["should_continue"] = bot_state != "OFF"

    if not state["should_continue"]:
        logger.info("Bot desactivado para este usuario")
    else:
        logger.debug("Bot activo", bot_state=bot_state)

    return state


def route_after_bot_check(state: ChatbotState) -> Literal["continue", "stop", "escalate"]:
    """Routing después de verificar estado del bot."""
    if state.get("gating_escalate"):
        return "escalate"
    return "continue" if state.get("should_continue", False) else "stop"


def extract_message_data(state: ChatbotState) -> ChatbotState:
    """
    Extrae todos los datos relevantes del mensaje.

    Corresponde al nodo 'Edit Fields' del workflow de n8n.
    Extrae: identifier, phone, name, account_id, conversation_id, etc.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con todos los datos extraídos
    """
    payload = state.get("raw_payload", {})
    body = payload.get("body", payload)
    conversation = body.get("conversation", {})
    messages = conversation.get("messages", [])

    # === CONFIGURACIÓN DEL AGENTE ===
    agente_config = body.get("agente_config", {})
    sp = agente_config.get("system_prompt")
    if isinstance(sp, str):
        state["system_prompt"] = sp
    
    temp = agente_config.get("temperatura")
    try:
        state["temperature"] = float(temp) if temp is not None else None
    except Exception:
        state["temperature"] = None
    
    mt = agente_config.get("max_tokens")
    try:
        state["max_tokens"] = int(mt) if mt is not None else None
    except Exception:
        state["max_tokens"] = None

    # === DATOS DE VERTICAL Y TENANT ===
    v_id = body.get("vertical_id") or state.get("vertical_id") or "restaurante"
    state["vertical_id"] = str(v_id).lower()

    empresa_config = body.get("empresa_config") or state.get("tenant_data") or {}
    state["tenant_data"] = empresa_config
    gsid = empresa_config.get("google_sheet_id") or ""
    state["google_sheet_id"] = str(gsid) if isinstance(gsid, str) else ""

    if not messages:
        logger.error("No hay mensajes para extraer datos")
        state["error"] = "No messages in payload"
        state["should_continue"] = False
        return state

    message = messages[0]

    # === USAR HELPER CENTRALIZADO ===
    common_fields = _extract_common_fields(body, message)
    state["identifier"] = common_fields["identifier"]
    state["phone_number"] = common_fields["phone_number"]
    state["user_name"] = common_fields["user_name"]
    state["account_id"] = common_fields["account_id"]
    state["conversation_id"] = common_fields["conversation_id"]
    state["contact_id"] = common_fields["contact_id"]
    state["current_message"] = common_fields["current_message"]
    state["tenant_id"] = common_fields["tenant_id"]
    state["tenant_slug"] = common_fields["tenant_slug"]
    state["namespaced_id"] = common_fields["namespaced_id"]
    if common_fields["_trace_id"]:
        state["_trace_id"] = common_fields["_trace_id"]

    if not state["conversation_id"]:
        state["error"] = "Missing conversation_id"
        state["should_continue"] = False
        return state

    # === MEMORIA CRM ===
    crm_raw = body.get("memoria_conversacional") or []
    crm_messages = []
    if isinstance(crm_raw, list):
        for it in crm_raw[-10:]:
            if isinstance(it, dict):
                role = it.get("role")
                content = it.get("content")
                if isinstance(role, str) and isinstance(content, str):
                    r = "user" if role.lower().startswith("u") else "assistant"
                    crm_messages.append({"role": r, "content": content})
    state["crm_memory"] = crm_messages

    # === RAG DOCS ===
    rag_raw = body.get("rag_docs") or []
    rag_list = []
    if isinstance(rag_raw, list):
        for d in rag_raw[:3]:
            if isinstance(d, dict):
                t = d.get("title")
                c = d.get("content")
                if isinstance(c, str):
                    rag_list.append({"title": str(t or ""), "content": c})
    state["rag_docs"] = rag_list

    # === GATING FLAGS ===
    gating_stop, gating_escalate = _extract_gating_flags(body)
    state["gating_stop"] = gating_stop
    state["gating_escalate"] = gating_escalate

    logger.info(
        "Datos extraídos del mensaje",
        identifier=state["identifier"],
        conversation_id=state["conversation_id"],
        content_type=state["current_message"]["content_type"],
    )

    return state
