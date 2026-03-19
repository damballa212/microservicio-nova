"""
Nodos de escalamiento.

Clasifica si la conversación necesita atención humana
y ejecuta el proceso de escalamiento si es necesario.
"""

from typing import Any, Literal

from src.config.constants import EscalationMessages, EscalationResponse
from src.models.state import ChatbotState
from src.nodes.decorators import handle_node_errors
from src.utils.logger import get_logger

logger = get_logger(__name__)


@handle_node_errors("classify_escalation")
async def classify_escalation(state: ChatbotState) -> ChatbotState:
    """
    Clasifica si la conversación requiere escalamiento humano.

    SIN LLAMADA LLM: usa el flag `requires_human` que ya retorna generate_response
    en su JSON, más un heurístico de palabras clave como safety net.

    El agente principal tiene todo el contexto para decidir escalamiento.
    Una segunda llamada LLM aquí sería redundante y cara.
    """
    state["_node_metrics"] = {
        "provider": "heuristic",
        "model_id": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }

    # 1. Gating forzado desde CRM — máxima prioridad
    if state.get("gating_escalate"):
        state["needs_escalation"] = True
        state["escalation_reason"] = "Escalamiento forzado por CRM"
        return state

    # 2. El agente principal ya marcó requires_human=true en su respuesta JSON
    #    generate_response() setea needs_escalation=True si el JSON del LLM lo indica.
    if state.get("needs_escalation"):
        if not state.get("escalation_reason"):
            state["escalation_reason"] = "model_flagged"
        logger.info("Escalamiento marcado por el agente principal", reason=state["escalation_reason"])
        return state

    # 3. Heurístico de palabras clave como safety net (sin LLM, gratis)
    chat_input = (state.get("chat_input") or "").lower()
    ESCALATION_KEYWORDS = {
        # Solicitud explícita de humano
        "quiero hablar con", "hablar con un agente", "hablar con una persona",
        "atención humana", "atiéndeme tú", "pon a alguien", "necesito a alguien",
        "llamar a un asesor", "llamar a un humano",
        # Frustración extrema
        "esto es una mierda", "qué asco de servicio", "pésimo servicio",
        "voy a denunciar", "voy a poner queja", "fraude", "me estafaron",
        # Emergencias
        "emergencia", "urgente", "accidente", "herido", "hospital",
    }
    if any(kw in chat_input for kw in ESCALATION_KEYWORDS):
        state["needs_escalation"] = True
        state["escalation_reason"] = "keyword_detected"
        logger.info("Escalamiento por palabra clave detectada")
        return state

    # 4. Sin escalamiento
    state["needs_escalation"] = False
    logger.debug("Sin escalamiento requerido")
    return state


def route_escalation(state: ChatbotState) -> Literal["escalate", "continue"]:
    """
    Routing basado en la clasificación de escalamiento.

    Returns:
        "escalate" si necesita humano, "continue" si no
    """
    return "escalate" if state.get("needs_escalation", False) else "continue"


async def escalate_to_human(state: ChatbotState) -> ChatbotState:
    """
    Ejecuta el proceso de escalamiento a humano.

    Corresponde a los nodos 'etiqueta_asistencia_ia' y 'apagar bot'.

    1. Agrega etiqueta a la conversación
    2. Desactiva el bot para este usuario
    3. (Opcional) Envía notificación por email

    Args:
        state: Estado actual del grafo

    Returns:
        Estado sin modificaciones significativas
    """
    conversation_id = state.get("conversation_id", 0)
    contact_id = state.get("contact_id", 0)
    state.get("phone_number", "")

    logger.info(
        "Iniciando escalamiento a humano",
        conversation_id=conversation_id,
        contact_id=contact_id,
    )

    try:
        state["needs_escalation"] = True
        if not state.get("escalation_reason"):
            state["escalation_reason"] = "Usuario requiere atención especializada"

        actions: dict[str, Any] = {}
        current_actions = state.get("actions")
        if isinstance(current_actions, dict):
            actions.update(current_actions)

        labels: list[str] = []
        raw_labels = actions.get("apply_labels")
        if isinstance(raw_labels, list):
            labels = [x for x in raw_labels if isinstance(x, str)]
        for lb in ["asistencia_ia", "escalado"]:
            if lb not in labels:
                labels.append(lb)
        actions["apply_labels"] = labels
        actions["set_ia_state"] = "OFF"
        actions["send_message"] = (
            "Te estoy conectando con uno de nuestros agentes. Por favor espera un momento."
        )
        state["actions"] = actions

        logger.info("Escalamiento marcado para ejecución externa", conversation_id=conversation_id)

    except Exception as e:
        logger.error(
            "Error durante escalamiento",
            error=str(e),
            conversation_id=conversation_id,
        )
        state["error"] = f"Escalation error: {str(e)}"

    return state
