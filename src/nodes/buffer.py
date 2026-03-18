"""
Nodos del sistema de buffer.

Implementa la lógica de consolidación de mensajes:
- add_to_buffer: Agrega mensaje al buffer Redis
- check_buffer_status: Determina si procesar, esperar o ignorar
- wait_for_messages: Espera 10 segundos antes de reintentar
"""

import asyncio
from typing import Literal

from src.buffer.buffer_manager import buffer_manager
from src.config.settings import settings
from src.models.state import ChatbotState
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def add_to_buffer(state: ChatbotState) -> ChatbotState:
    """
    Agrega el mensaje actual al buffer del usuario.

    Corresponde al nodo 'Redis (Push al Buffer)' de n8n.
    El mensaje se guarda en una lista Redis con TTL de 1 hora.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado sin modificaciones importantes (solo logging)
    """
    identifier = state.get("namespaced_id") or state.get("identifier", "")
    current_message = state.get("current_message", {})

    if not identifier:
        logger.error("No hay identifier para el buffer")
        state["error"] = "Missing identifier"
        state["should_continue"] = False
        return state

    # Agregar al buffer
    count = await buffer_manager.add_message(identifier, current_message)

    logger.debug(
        "Mensaje agregado al buffer",
        identifier=identifier,
        buffer_count=count,
    )

    return state


async def check_buffer_status(state: ChatbotState) -> ChatbotState:
    """
    Verifica el estado del buffer y determina la acción.

    Corresponde al nodo 'Switch' de n8n.
    Determina si:
    - duplicate: El mensaje ya fue procesado
    - wait: El usuario sigue escribiendo
    - process: Listo para procesar

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con buffer_action actualizado
    """
    identifier = state.get("namespaced_id") or state.get("identifier", "")
    current_message = state.get("current_message", {})
    source_id = current_message.get("source_id", "")

    if not identifier:
        state["buffer_action"] = "skip"
        return state

    # Verificar estado del buffer
    action = await buffer_manager.check_status(identifier, source_id)
    state["buffer_action"] = action

    logger.debug(
        "Estado del buffer verificado",
        identifier=identifier,
        action=action,
    )

    return state


async def wait_for_messages(state: ChatbotState) -> ChatbotState:
    """
    Espera el tiempo configurado antes de revisar el buffer nuevamente.

    Corresponde al nodo 'Wait' de n8n.
    Espera settings.buffer_wait_seconds (default: 10 segundos).

    LIMITACIÓN DE ESCALABILIDAD:
    Este nodo bloquea el worker durante la espera, lo que puede limitar
    la concurrencia bajo alta carga. Con N workers, solo N usuarios pueden
    estar en espera simultáneamente.

    RECOMENDACIONES DE OPTIMIZACIÓN:
    1. Reducir buffer_wait_seconds a 3-5 segundos para alta concurrencia
    2. Incrementar el número de workers según la carga esperada
    3. Para arquitecturas de muy alta escala (>100 usuarios concurrentes),
       considerar migrar a un sistema basado en eventos Redis Pub/Sub
       que despierte workers solo cuando el buffer esté listo.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado sin modificaciones (solo espera)
    """
    wait_seconds = settings.buffer_wait_seconds

    logger.debug(
        "Esperando mensajes adicionales",
        wait_seconds=wait_seconds,
        identifier=state.get("namespaced_id") or state.get("identifier", "unknown"),
    )

    await asyncio.sleep(wait_seconds)

    return state


def route_buffer_decision(state: ChatbotState) -> Literal["wait", "process", "duplicate"]:
    """
    Routing basado en la decisión del buffer.

    Returns:
        - "wait": Volver a check_buffer_status después de esperar
        - "process": Continuar al procesamiento multimodal
        - "duplicate": Terminar (END)
    """
    action = state.get("buffer_action", "skip")

    if action == "process":
        return "process"
    elif action == "wait":
        return "wait"
    else:  # duplicate, skip, o cualquier otro
        return "duplicate"


async def get_buffer_messages(state: ChatbotState) -> ChatbotState:
    """
    Obtiene todos los mensajes del buffer y los almacena en el estado.

    Corresponde al nodo 'Redis1 (Leer Buffer)' + 'Redis2 (Limpiar Buffer)'.
    Lee los mensajes y limpia el buffer.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con buffer_messages poblado
    """
    identifier = state.get("namespaced_id") or state.get("identifier", "")

    if not identifier:
        state["buffer_messages"] = []
        return state

    # Obtener mensajes
    messages = await buffer_manager.get_messages(identifier)

    # Limpiar buffer
    await buffer_manager.clear(identifier)

    state["buffer_messages"] = messages

    logger.info(
        "Mensajes obtenidos del buffer",
        identifier=identifier,
        message_count=len(messages),
    )

    return state
