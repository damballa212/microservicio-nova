"""Nodo de envío de mensajes."""

from src.models.state import ChatbotState
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def send_messages(state: ChatbotState) -> ChatbotState:
    """
    Prepara mensajes formateados para envío por el sistema externo.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado sin modificaciones (solo logging)
    """
    formatted_parts = state.get("formatted_parts", [])
    conversation_id = state.get("conversation_id", 0)

    if not formatted_parts:
        logger.warning("No hay partes para enviar")
        return state

    if not conversation_id:
        logger.warning("No hay conversation_id")
        return state

    try:
        state["outbound_message_parts"] = list(formatted_parts)
        state["outbound_conversation_id"] = conversation_id
        logger.info(
            "Mensajes listos para envío externo",
            conversation_id=conversation_id,
            total_parts=len(formatted_parts),
        )

    except Exception as e:
        logger.error(
            "Error preparando mensajes",
            error=str(e),
            conversation_id=conversation_id,
        )
        state["error"] = f"Error preparing messages: {str(e)}"

    return state
