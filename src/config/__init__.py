"""
Módulo de configuración.

Contiene la configuración centralizada del proyecto y los prompts del sistema.
"""

from src.config.prompts import BUSINESS_PROMPT, CLASSIFIER_PROMPT, FORMATTER_PROMPT
from src.config.settings import settings

__all__ = ["settings", "BUSINESS_PROMPT", "FORMATTER_PROMPT", "CLASSIFIER_PROMPT"]
