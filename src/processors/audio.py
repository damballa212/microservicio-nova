"""
Procesador de mensajes de audio.

Transcribe mensajes de voz usando OpenAI Whisper.
"""

from src.integrations.openai_client import openai_client
from src.models.state import MessageData
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AudioProcessor:
    """
    Procesador para mensajes de audio.

    Descarga el archivo de audio desde la URL del sistema origen
    y lo transcribe usando OpenAI Whisper.
    """

    async def process(self, message: dict) -> MessageData:
        """
        Procesa un mensaje de audio.

        1. Obtiene la URL del archivo de audio
        2. Descarga y transcribe con Whisper
        3. Retorna el texto transcrito como contenido

        Args:
            message: Diccionario con datos del mensaje

        Returns:
            MessageData con la transcripción como contenido
        """
        # Obtener URL del audio
        attachments = message.get("attachments", [])
        audio_url = ""

        if attachments and len(attachments) > 0:
            audio_url = attachments[0].get("data_url", "")

        if not audio_url:
            logger.warning("No se encontró URL de audio en el mensaje")
            return MessageData(
                content="[Audio no disponible]",
                content_type="audio",
                source_id=message.get("source_id", ""),
                created_at=message.get("created_at", ""),
            )

        logger.info("Transcribiendo audio", url=audio_url[:50])

        try:
            # Transcribir audio
            transcription = await openai_client.transcribe_audio(audio_url)

            logger.info(
                "Audio transcrito exitosamente",
                transcription_length=len(transcription),
            )

            return MessageData(
                content=transcription,
                content_type="audio",
                source_id=message.get("source_id", ""),
                created_at=message.get("created_at", ""),
                info_imagen=None,
            )

        except Exception as e:
            logger.error("Error transcribiendo audio", error=str(e))
            return MessageData(
                content=f"[Error transcribiendo audio: {str(e)}]",
                content_type="audio",
                source_id=message.get("source_id", ""),
                created_at=message.get("created_at", ""),
            )
