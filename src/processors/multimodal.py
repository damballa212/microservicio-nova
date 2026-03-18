"""
Orquestador de procesamiento multimodal.

Coordina el procesamiento de diferentes tipos de contenido:
texto, audio e imagen. Determina el tipo de cada mensaje
y lo envía al procesador correspondiente.
"""

from typing import Any

from src.models.state import MessageData
from src.processors.audio import AudioProcessor
from src.processors.image import ImageProcessor
from src.processors.text import TextProcessor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MultimodalProcessor:
    """
    Orquestador de procesamiento multimodal.

    Procesa una lista de mensajes de diferentes tipos
    y los convierte todos a un formato unificado.

    El resultado es una lista de MessageData ordenada por timestamp,
    donde todo el contenido está en formato texto (audio transcrito,
    imágenes con descripción).

    Ejemplo:
        processor = MultimodalProcessor()

        messages = [
            {"content": "Hola", "content_type": "text", ...},
            {"attachments": [...], "content_type": "audio", ...},
            {"attachments": [...], "content_type": "image", ...},
        ]

        processed = await processor.process_messages(messages)
        # Todos los mensajes ahora tienen content como texto
    """

    def __init__(self):
        """Inicializa los procesadores."""
        self.text_processor: TextProcessor = TextProcessor()
        self.audio_processor: AudioProcessor = AudioProcessor()
        self.image_processor: ImageProcessor = ImageProcessor()

    def _get_content_type(self, message: dict[str, Any]) -> str:
        """
        Determina el tipo de contenido de un mensaje.

        Primero verifica content_type explícito, luego
        infiere del tipo de attachment.

        Args:
            message: Diccionario con datos del mensaje

        Returns:
            Tipo de contenido: "text", "audio" o "image"
        """
        content_type = str(message.get("content_type") or "text")

        # Si tiene attachments, verificar el tipo
        attachments = message.get("attachments") or []
        if isinstance(attachments, list) and len(attachments) > 0:
            first = attachments[0] if isinstance(attachments[0], dict) else {}
            file_type = str(first.get("file_type") or "")
            if file_type in ("audio", "image", "video"):
                return file_type

        return content_type

    async def process_message(self, message: dict[str, Any]) -> MessageData:
        """
        Procesa un mensaje individual.

        Determina el tipo y lo envía al procesador correspondiente.

        Args:
            message: Diccionario con datos del mensaje

        Returns:
            MessageData procesado
        """
        content_type = self._get_content_type(message)

        logger.debug(
            "Procesando mensaje",
            content_type=content_type,
            source_id=message.get("source_id", "")[:20],
        )

        if content_type == "text":
            return await self.text_processor.process(message)
        elif content_type == "audio":
            return await self.audio_processor.process(message)
        elif content_type == "image":
            return await self.image_processor.process(message)
        else:
            # Tipo desconocido, tratar como texto
            logger.warning(
                "Tipo de contenido desconocido, tratando como texto",
                content_type=content_type,
            )
            return await self.text_processor.process(message)

    async def process_messages(self, messages: list[dict[str, Any]]) -> list[MessageData]:
        """
        Procesa una lista de mensajes.

        1. Procesa cada mensaje según su tipo
        2. Ordena por timestamp
        3. Retorna lista unificada

        Args:
            messages: Lista de diccionarios con mensajes

        Returns:
            Lista de MessageData procesados y ordenados
        """
        if not messages:
            return []

        logger.info(
            "Iniciando procesamiento multimodal",
            message_count=len(messages),
        )

        processed = []
        for message in messages:
            try:
                result = await self.process_message(message)
                processed.append(result)
            except Exception as e:
                logger.error(
                    "Error procesando mensaje",
                    error=str(e),
                    source_id=message.get("source_id", ""),
                )
                # Agregar mensaje de error pero continuar
                processed.append(
                    MessageData(
                        content=f"[Error procesando mensaje: {str(e)}]",
                        content_type="text",
                        source_id=message.get("source_id", ""),
                        created_at=message.get("created_at", ""),
                    )
                )

        # Ordenar por timestamp
        processed.sort(key=lambda m: m.created_at)

        logger.info(
            "Procesamiento multimodal completado",
            processed_count=len(processed),
        )

        return processed

    def consolidate_to_chat_input(self, messages: list[MessageData]) -> tuple[str, str | None]:
        """
        Consolida mensajes procesados en un chat_input para el agente.

        Combina todos los contenidos en un string separado por newlines.
        Si hay info_imagen, la concatena al final.

        Args:
            messages: Lista de MessageData procesados

        Returns:
            Tupla (chat_input, info_imagen consolidada)
        """
        contents = []
        image_infos = []

        for msg in messages:
            if msg.content:
                contents.append(msg.content)
            if msg.info_imagen:
                image_infos.append(msg.info_imagen)

        chat_input = "\n".join(contents)
        info_imagen = "\n---\n".join(image_infos) if image_infos else None

        return chat_input, info_imagen


# Instancia global
multimodal_processor = MultimodalProcessor()
