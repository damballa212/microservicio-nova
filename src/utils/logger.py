"""
Configuración de logging estructurado.

Usa structlog para logs JSON en producción y logs coloridos en desarrollo.
"""

import logging
import sys
from typing import Any, cast

import structlog

from src.config.settings import settings


def setup_logging() -> None:
    """
    Configura el sistema de logging.

    En desarrollo: logs coloridos y legibles.
    En producción: logs JSON para fácil parseo.
    """
    # Configurar nivel de logging
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Procesadores comunes
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.is_development:
        # Desarrollo: logs coloridos
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]
    else:
        # Producción: logs JSON
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=cast(Any, processors),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configurar logging estándar de Python para librerías externas
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """
    Obtiene un logger configurado.

    Args:
        name: Nombre del logger (usualmente __name__)

    Returns:
        Logger estructurado

    Ejemplo:
        logger = get_logger(__name__)
        logger.info("Mensaje de log", extra_field="valor")
    """
    return cast(structlog.BoundLogger, structlog.get_logger(name))


# Logger por defecto
logger = get_logger("chatbot")
