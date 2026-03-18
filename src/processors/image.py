"""
Procesador de mensajes con imágenes.

Analiza imágenes usando GPT-4 Vision para extraer información útil.
"""

from src.integrations.openai_client import openai_client
from src.models.state import MessageData
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """
    Procesador para mensajes con imágenes.

    Descarga la imagen desde la URL del sistema origen
    y la analiza usando GPT-4 Vision para extraer información.
    """

    async def process(self, message: dict) -> MessageData:
        """
        Procesa un mensaje con imagen.

        1. Obtiene la URL de la imagen
        2. Analiza la imagen con GPT-4 Vision
        3. Retorna el contenido original + análisis en info_imagen

        Args:
            message: Diccionario con datos del mensaje

        Returns:
            MessageData con el análisis de la imagen
        """
        # Obtener URL de la imagen
        attachments = message.get("attachments", [])
        image_url = ""

        if attachments and len(attachments) > 0:
            image_url = attachments[0].get("data_url", "")

        if not image_url:
            logger.warning("No se encontró URL de imagen en el mensaje")
            return MessageData(
                content=message.get("content", ""),
                content_type="image",
                source_id=message.get("source_id", ""),
                created_at=message.get("created_at", ""),
                info_imagen="[Imagen no disponible]",
            )

        logger.info("Analizando imagen", url=image_url[:50])

        try:
            # Analizar imagen
            analysis = await openai_client.analyze_image(image_url)

            logger.info(
                "Imagen analizada exitosamente",
                analysis_length=len(analysis),
            )

            return MessageData(
                content=message.get("content", ""),
                content_type="image",
                source_id=message.get("source_id", ""),
                created_at=message.get("created_at", ""),
                attachments=attachments,
                info_imagen=analysis,
            )

        except Exception as e:
            logger.error("Error analizando imagen", error=str(e))
            return MessageData(
                content=message.get("content", ""),
                content_type="image",
                source_id=message.get("source_id", ""),
                created_at=message.get("created_at", ""),
                info_imagen=f"[Error analizando imagen: {str(e)}]",
            )
