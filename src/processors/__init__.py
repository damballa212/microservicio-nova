"""
Módulo de procesadores multimodal.

Contiene procesadores para diferentes tipos de contenido:
- Texto: Extracción directa
- Audio: Transcripción con Whisper
- Imagen: Análisis con GPT-4 Vision
"""

from src.processors.audio import AudioProcessor
from src.processors.image import ImageProcessor
from src.processors.multimodal import MultimodalProcessor
from src.processors.text import TextProcessor

__all__ = [
    "TextProcessor",
    "AudioProcessor",
    "ImageProcessor",
    "MultimodalProcessor",
]
