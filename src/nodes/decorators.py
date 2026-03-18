"""
Decoradores y utilidades para nodos del grafo.

Proporciona manejo de errores consistente, logging
estructurado, y métricas para todos los nodos.
"""

import functools
from datetime import datetime
from typing import Any, Callable, TypeVar

from src.config.constants import ErrorMessages
from src.models.state import ChatbotState
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Type variables para preservar tipos en decoradores
F = TypeVar("F", bound=Callable[..., Any])


def handle_node_errors(
    node_name: str,
    fallback_response: str | None = None,
    set_error_in_state: bool = True,
    continue_on_error: bool = True,
) -> Callable[[F], F]:
    """
    Decorador para manejo de errores consistente en nodos del grafo.
    
    Proporciona:
    - Logging estructurado con contexto del nodo
    - Captura de excepciones con información detallada
    - Opcionalmente establece respuesta de fallback
    - Opcionalmente permite continuar el flujo
    
    Args:
        node_name: Nombre del nodo para logging
        fallback_response: Respuesta a usar si hay error (para nodos que generan respuestas)
        set_error_in_state: Si True, guarda el error en state["error"]
        continue_on_error: Si True, retorna el state modificado; si False, re-lanza la excepción
        
    Example:
        @handle_node_errors("generate_response", fallback_response="Lo siento...")
        async def generate_response(state: ChatbotState) -> ChatbotState:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(state: ChatbotState, *args: Any, **kwargs: Any) -> ChatbotState:
            start_time = datetime.now()
            identifier = state.get("identifier", "unknown")
            execution_id = state.get("_execution_id", "")
            
            try:
                result = await func(state, *args, **kwargs)
                
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.debug(
                    f"Nodo {node_name} completado",
                    node=node_name,
                    identifier=identifier,
                    execution_id=execution_id,
                    duration_ms=round(duration_ms, 2),
                )
                
                return result
                
            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                logger.error(
                    f"Error en nodo {node_name}",
                    node=node_name,
                    identifier=identifier,
                    execution_id=execution_id,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                
                if set_error_in_state:
                    state["error"] = f"[{node_name}] {str(e)}"
                
                if fallback_response is not None:
                    state["ai_response"] = fallback_response
                
                if continue_on_error:
                    return state
                else:
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(state: ChatbotState, *args: Any, **kwargs: Any) -> ChatbotState:
            start_time = datetime.now()
            identifier = state.get("identifier", "unknown")
            execution_id = state.get("_execution_id", "")
            
            try:
                result = func(state, *args, **kwargs)
                
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.debug(
                    f"Nodo {node_name} completado",
                    node=node_name,
                    identifier=identifier,
                    execution_id=execution_id,
                    duration_ms=round(duration_ms, 2),
                )
                
                return result
                
            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                logger.error(
                    f"Error en nodo {node_name}",
                    node=node_name,
                    identifier=identifier,
                    execution_id=execution_id,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                
                if set_error_in_state:
                    state["error"] = f"[{node_name}] {str(e)}"
                
                if fallback_response is not None:
                    state["ai_response"] = fallback_response
                
                if continue_on_error:
                    return state
                else:
                    raise
        
        # Determinar si la función es async o sync
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore
    
    return decorator


def log_node_execution(node_name: str) -> Callable[[F], F]:
    """
    Decorador simple para logging de ejecución de nodos sin manejo de errores.
    
    Útil para nodos donde quieres logging pero no quieres capturar errores.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(state: ChatbotState, *args: Any, **kwargs: Any) -> ChatbotState:
            start_time = datetime.now()
            identifier = state.get("identifier", "unknown")
            
            logger.info(f"Iniciando nodo {node_name}", node=node_name, identifier=identifier)
            
            result = await func(state, *args, **kwargs)
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"Nodo {node_name} completado",
                node=node_name,
                identifier=identifier,
                duration_ms=round(duration_ms, 2),
            )
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(state: ChatbotState, *args: Any, **kwargs: Any) -> ChatbotState:
            start_time = datetime.now()
            identifier = state.get("identifier", "unknown")
            
            logger.info(f"Iniciando nodo {node_name}", node=node_name, identifier=identifier)
            
            result = func(state, *args, **kwargs)
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"Nodo {node_name} completado",
                node=node_name,
                identifier=identifier,
                duration_ms=round(duration_ms, 2),
            )
            
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore
    
    return decorator
