from typing import Annotated

from langchain_core.tools import tool

from src.memory.semantic_memory import search_episodes
from src.nodes.knowledge import _find_best_inventory_matches, _rows_from_sheet_values, _summarize_inventory_matches
from src.rag.vector_store import reranked_search
from src.utils.logger import get_logger

logger = get_logger(__name__)


@tool
async def rag_search(
    query: Annotated[str, "Consulta específica para buscar en documentos (ej: 'precios pizza', 'política devoluciones')"],
    tenant_id: Annotated[str, "ID de la empresa (tenant)"],
) -> str:
    """
    Busca información oficial en la base de conocimiento de documentos del negocio.
    Usa esta herramienta para responder sobre:
    - Menú, ingredientes, precios de productos
    - Políticas de servicio, horarios, ubicación
    - Historia de la empresa, preguntas frecuentes
    
    NO usar para:
    - Stock en tiempo real (usa inventory_lookup)
    - Recuerdos de conversaciones pasadas (usa semantic_memory_search)
    """
    try:
        # Usamos top_k=5 para tener buen contexto
        docs = await reranked_search(tenant_id, query, top_k=5)
        
        if not docs:
            return "No se encontró información relevante en los documentos del negocio."
        
        # Formatear resultados para el LLM
        result_text = f"Resultados de búsqueda en documentos para '{query}':\n\n"
        for i, doc in enumerate(docs[:3], 1):  # Limitamos a los top 3 para no saturar contexto
            title = doc.get("title", "Sin título")
            content = doc.get("content", "")
            # Truncar contenido muy largo si es necesario, aunque el chunking ya limita
            result_text += f"DOC {i} [{title}]:\n{content}\n---\n"
            
        return result_text
    except Exception as e:
        logger.error(f"Error en rag_search: {str(e)}")
        return "Hubo un error técnico consultando la base de conocimiento."


@tool
async def inventory_lookup(
    product_query: Annotated[str, "Nombre o descripción del producto a buscar en inventario"],
    sheet_id: Annotated[str, "ID del Google Sheet de inventario"],
) -> str:
    """
    Consulta el inventario y stock en tiempo real desde Google Sheets.
    Usa esta herramienta cuando el usuario pregunte explícitamente sobre:
    - Disponibilidad o existencia de un producto
    - "¿Tienen X?", "¿Les queda Y?"
    - Cantidades disponibles
    """
    if not sheet_id:
        return "Error: No hay un ID de hoja de inventario configurado para este negocio."

    try:
        # Reutilizamos la lógica existente en knowledge.py pero desacoplada del state global
        # 1. Obtener filas (esto maneja caché interna y auth)
        rows = await _rows_from_sheet_values(sheet_id)
        
        if not rows:
            return "No se pudo leer el inventario (hoja vacía o error de conexión)."
            
        # 2. Buscar coincidencias
        matches = _find_best_inventory_matches(rows, product_query)
        
        if not matches:
            return f"No encontré productos en el inventario que coincidan con '{product_query}'."
            
        # 3. Resumir resultados
        summary = _summarize_inventory_matches(matches)
        return f"Resultados del inventario en tiempo real:\n{summary}"
        
    except Exception as e:
        logger.error(f"Error en inventory_lookup: {str(e)}")
        return "Hubo un error técnico consultando el inventario."


@tool
async def semantic_memory_search(
    query: Annotated[str, "Pregunta sobre el historial (ej: 'qué pedí la última vez', 'mi dirección usual')"],
    identifier: Annotated[str, "ID único del usuario (identifier)"],
    tenant_id: Annotated[str, "ID de la empresa (tenant)"],
) -> str:
    """
    Busca en la memoria a largo plazo (episodios pasados) de este usuario.
    Usa esta herramienta cuando:
    - El usuario hace referencia al pasado ("como la otra vez")
    - Pregunta por sus preferencias o datos guardados
    - Necesitas contexto de conversaciones anteriores (más allá del historial reciente)
    """
    try:
        # Buscamos episodios semánticamente relevantes
        episodes = search_episodes(tenant_id, identifier, query, top_k=3)
        
        if not episodes:
            return "No encontré recuerdos relevantes de conversaciones anteriores con este usuario."
        
        text = f"Memoria a largo plazo recuperada para '{query}':\n\n"
        for ep in episodes:
            date_str = ep.get('started_at', '')
            # Formatear fecha para ser amigable (YYYY-MM-DD)
            if date_str and len(date_str) >= 10:
                date_str = date_str[:10]
                
            summary = ep.get('summary', '')
            text += f"EPISODIO DEL {date_str}:\n{summary}\n---\n"
            
        return text
    except Exception as e:
        logger.error(f"Error en semantic_memory_search: {str(e)}")
        return "Hubo un error consultando la memoria a largo plazo."
