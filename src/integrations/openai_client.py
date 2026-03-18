"""
Cliente para OpenAI.

Proporciona acceso a:
- Whisper: Transcripción de audio
- GPT-4 Vision: Análisis de imágenes
- GPT-4o-mini: Corrección de formato
"""

import io

import httpx
from openai import AsyncOpenAI

from src.config.prompts import IMAGE_ANALYSIS_PROMPT
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """
    Cliente async para la API de OpenAI.

    Proporciona métodos para:
    - Transcribir audio con Whisper
    - Analizar imágenes con GPT-4 Vision

    Soporta OpenRouter como proveedor alternativo.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        """
        Inicializa el cliente de OpenAI.

        Args:
            api_key: API key de OpenAI (default: settings.openai_api_key)
            base_url: Base URL (default: settings.openai_base_url, para OpenRouter)
        """
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url if self.base_url != "https://api.openai.com/v1" else None,
        )

    async def _download_file(self, url: str) -> bytes:
        """
        Descarga un archivo desde una URL.

        Args:
            url: URL del archivo

        Returns:
            Contenido del archivo como bytes
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            return response.content

    async def transcribe_audio(
        self,
        audio_url: str,
        language: str = "es",
    ) -> str:
        """
        Transcribe un archivo de audio usando Whisper.

        Args:
            audio_url: URL del archivo de audio
            language: Código de idioma (default: español)

        Returns:
            Texto transcrito
        """
        logger.info("Iniciando transcripción de audio", url=audio_url[:50])

        try:
            # Descargar audio
            audio_bytes = await self._download_file(audio_url)

            # Crear archivo en memoria
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.ogg"  # Whisper necesita un nombre de archivo

            # Transcribir
            transcription = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
            )

            text = transcription.text

            logger.info(
                "Audio transcrito exitosamente",
                text_length=len(text),
            )

            return text

        except Exception as e:
            logger.error("Error transcribiendo audio", error=str(e))
            raise

    async def analyze_image(
        self,
        image_url: str,
        prompt: str | None = None,
        max_tokens: int = 500,
    ) -> str:
        """
        Analiza una imagen usando GPT-4 Vision.

        Args:
            image_url: URL de la imagen
            prompt: Prompt personalizado (default: IMAGE_ANALYSIS_PROMPT)
            max_tokens: Máximo de tokens en la respuesta

        Returns:
            Descripción/análisis de la imagen
        """
        logger.info("Iniciando análisis de imagen", url=image_url[:50])

        analysis_prompt = prompt or IMAGE_ANALYSIS_PROMPT

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                        ],
                    }
                ],
                max_tokens=max_tokens,
            )

            analysis = response.choices[0].message.content or ""

            logger.info(
                "Imagen analizada exitosamente",
                analysis_length=len(analysis),
            )

            return analysis

        except Exception as e:
            logger.error("Error analizando imagen", error=str(e))
            raise

    async def fix_json(self, broken_json: str) -> str:
        """
        Intenta corregir un JSON malformado usando GPT-4o-mini.

        Args:
            broken_json: JSON potencialmente malformado

        Returns:
            JSON corregido
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Corrige el siguiente JSON y devuélvelo válido. Solo responde con el JSON, sin explicaciones.",
                    },
                    {
                        "role": "user",
                        "content": broken_json,
                    },
                ],
                temperature=0.1,
            )

            return response.choices[0].message.content or broken_json

        except Exception as e:
            logger.error("Error corrigiendo JSON", error=str(e))
            return broken_json


# Instancia global
openai_client = OpenAIClient()
