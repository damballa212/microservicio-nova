"""
Nodo de procesamiento multimodal.

Procesa todos los mensajes del buffer según su tipo
(texto, audio, imagen) y prepara el input para el agente.

REFACTORIZACIÓN: Usa claim_and_clear para operación atómica
y evitar race conditions donde mensajes se pierden.
"""

from src.buffer.buffer_manager import buffer_manager
from src.models.state import ChatbotState
from src.processors.multimodal import multimodal_processor
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Keywords para detectar consultas de inventario
INVENTORY_KEYWORDS = ["inventario", "stock", "disponible", "hay", "quedan", "tienen"]


async def process_multimodal(state: ChatbotState) -> ChatbotState:
    """
    Procesa todos los mensajes del buffer de forma multimodal.

    Corresponde a los nodos 11-25 del workflow de n8n:
    - Split Out
    - JSON Parse
    - If (Clasificación de Tipo)
    - Descargar Imagen / Audio
    - Analyze Image / Transcribe Audio
    - Merge
    - Sort
    - Aggregate
    - Chat Input

    IMPORTANTE: Usa claim_and_clear() para operación atómica
    y evitar race conditions.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con processed_messages, chat_input e info_imagen
    """
    identifier = state.get("namespaced_id") or state.get("identifier", "")

    # Operación ATÓMICA: obtener y limpiar buffer en una sola transacción
    # Esto evita que mensajes se pierdan si llegan mientras procesamos
    messages = await buffer_manager.claim_and_clear(identifier)

    if not messages:
        logger.warning("No hay mensajes para procesar", identifier=identifier)
        state["processed_messages"] = []
        state["chat_input"] = ""
        state["info_imagen"] = None
        state["inventory_query"] = None
        return state

    # Convertir MessageData a dict para el procesador
    message_dicts = [msg.model_dump() for msg in messages]

    logger.info(
        "Iniciando procesamiento multimodal",
        message_count=len(messages),
        identifier=identifier,
    )

    # Procesar mensajes (texto, audio, imagen)
    processed = await multimodal_processor.process_messages(message_dicts)

    # Consolidar en chat_input
    chat_input, info_imagen = multimodal_processor.consolidate_to_chat_input(processed)

    # Actualizar estado
    state["processed_messages"] = processed
    state["chat_input"] = chat_input
    state["info_imagen"] = info_imagen

    # Detectar si es consulta de inventario
    lower_input = (chat_input or "").lower()
    inventory_query = chat_input if any(kw in lower_input for kw in INVENTORY_KEYWORDS) else None
    state["inventory_query"] = inventory_query

    logger.info(
        "Procesamiento multimodal completado",
        processed_count=len(processed),
        chat_input_length=len(chat_input),
        has_image_info=bool(info_imagen),
        is_inventory_query=bool(inventory_query),
    )

    return state
