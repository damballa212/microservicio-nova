"""
Nodo de formateo de respuestas.

Divide respuestas largas en partes para WhatsApp.

REFACTORIZACIÓN: Detecta y extrae texto de JSON crudo si el
parsing del LLM falló, evitando enviar JSON al usuario.
"""

import json
import re
from typing import Any

from src.models.state import ChatbotState
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _extract_text_from_json(text: str) -> str | None:
    """
    Intenta extraer response_text de un JSON si el texto parece ser JSON.
    
    Esto es un safety net para cuando el ai_agent falla en parsear
    el JSON del LLM y pasa el JSON crudo.
    
    Returns:
        El texto extraído o None si no es JSON
    """
    stripped = text.strip()
    
    # Verificar si parece JSON
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return None
    
    try:
        # Intentar parsear
        data = json.loads(stripped)
        
        if isinstance(data, dict):
            # Buscar response_text o response
            response = data.get("response_text") or data.get("response") or data.get("text")
            if isinstance(response, str) and response:
                logger.warning(
                    "Formatter detectó JSON crudo, extrayendo response_text",
                    original_length=len(text),
                    extracted_length=len(response),
                )
                return response
    except json.JSONDecodeError:
        pass
    
    return None


def _extract_text_from_markdown_json(text: str) -> str | None:
    """
    Extrae response_text de JSON envuelto en markdown (```json ... ```).
    """
    # Buscar bloques de código JSON
    match = re.search(r"```(?:json)?\s*\n?({.*?})\s*\n?```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                response = data.get("response_text") or data.get("response")
                if isinstance(response, str) and response:
                    logger.warning(
                        "Formatter detectó JSON en markdown, extrayendo response_text"
                    )
                    return response
        except json.JSONDecodeError:
            pass
    
    return None


def sanitize_response(text: str) -> str:
    """
    Sanitiza la respuesta antes de formatear.
    
    1. Detecta y extrae texto de JSON si es necesario
    2. Limpia caracteres problemáticos para WhatsApp
    """
    if not text:
        return ""
    
    # Verificar si es JSON crudo y extraer texto
    extracted = _extract_text_from_json(text)
    if extracted:
        text = extracted
    else:
        # Verificar si tiene JSON en markdown
        extracted_md = _extract_text_from_markdown_json(text)
        if extracted_md:
            text = extracted_md
    
    return text


def clean_response_for_whatsapp(text: str) -> str:
    """
    Limpia el texto para WhatsApp.

    Elimina caracteres que no se ven bien en WhatsApp:
    - Asteriscos (markdown)
    - Hashtags
    - Signos de interrogación/exclamación invertidos

    Args:
        text: Texto a limpiar

    Returns:
        Texto limpio
    """
    # Primero sanitizar (detectar JSON)
    text = sanitize_response(text)
    
    # Eliminar asteriscos
    text = text.replace("*", "")
    # Eliminar hashtags
    text = text.replace("#", "")
    # Eliminar signos invertidos
    text = text.replace("¿", "")
    text = text.replace("¡", "")
    # Limpiar saltos de línea múltiples
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


async def format_response(state: ChatbotState) -> ChatbotState:
    """
    Formatea la respuesta dividiéndola en partes si es necesario.

    Corresponde al nodo 'Basic LLM Chain' del workflow de n8n.
    Divide respuestas largas en 1-3 partes para simular
    conversación natural en WhatsApp.

    IMPORTANTE: Este nodo detecta si ai_response es JSON crudo
    y extrae el texto automáticamente.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con formatted_parts poblado
    """
    ai_response = state.get("ai_response", "")

    if not ai_response:
        state["formatted_parts"] = []
        return state

    # Limpiar respuesta (incluye detección de JSON)
    clean_response = clean_response_for_whatsapp(ai_response)

    # Si después de limpiar quedó vacío, reportar error
    if not clean_response:
        logger.error("Respuesta vacía después de limpieza")
        clean_response = "Lo siento, tuve un problema procesando mi respuesta."

    logger.info(
        "Formateando respuesta",
        original_length=len(ai_response),
        cleaned_length=len(clean_response),
    )

    # Usar división inteligente sin LLM (más rápido y sin errores)
    parts = smart_split(clean_response)
    state["formatted_parts"] = parts

    logger.info(
        "Respuesta formateada",
        total_parts=len(parts),
    )

    return state


def smart_split(text: str, max_parts: int = 3, max_chars: int = 500) -> list[str]:
    """
    Divide texto de forma inteligente.

    Intenta dividir en puntos naturales (punto seguido, fin de oración).

    Args:
        text: Texto a dividir
        max_parts: Máximo número de partes
        max_chars: Caracteres máximos por parte

    Returns:
        Lista de partes
    """
    if not text:
        return []
    
    if len(text) <= max_chars:
        return [text]

    # Dividir por oraciones
    sentences = re.split(r"(?<=[.!?])\s+", text)

    parts: list[str] = []
    current_part = ""

    for i, sentence in enumerate(sentences):
        if len(current_part) + len(sentence) <= max_chars:
            current_part += (" " if current_part else "") + sentence
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = sentence

            if len(parts) >= max_parts - 1:
                # Última parte, agregar todo lo restante
                remaining = " ".join(sentences[i:])
                parts.append(remaining.strip())
                current_part = ""
                break

    if current_part:
        parts.append(current_part.strip())

    # Si tenemos más partes de las permitidas, consolidar
    while len(parts) > max_parts:
        # Combinar las dos últimas
        parts[-2] = parts[-2] + " " + parts[-1]
        parts.pop()

    return parts if parts else [text]
