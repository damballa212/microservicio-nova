"""
Procesador de mensajes de texto.

Extrae el contenido de texto directamente, sin transformación adicional.
"""

from src.models.state import MessageData
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TextProcessor:
    """
    Procesador para mensajes de texto.

    El procesamiento de texto es directo: simplemente extrae
    el contenido y el timestamp del mensaje.
    """

    async def process(self, message: dict) -> MessageData:
        """
        Procesa un mensaje de texto.

        Args:
            message: Diccionario con datos del mensaje

        Returns:
            MessageData con el contenido procesado
        """
        content = message.get("content", "")

        logger.debug(
            "Procesando mensaje de texto",
            content_length=len(content),
        )

        return MessageData(
            content=content,
            content_type="text",
            source_id=message.get("source_id", ""),
            created_at=message.get("created_at", ""),
            info_imagen=None,
        )
