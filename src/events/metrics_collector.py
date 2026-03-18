"""
Metrics Collector para métricas de ejecución y LLM.

Maneja la recolección, almacenamiento y cálculo de métricas.
Separado de EventEmitter para cumplir Single Responsibility Principle.
"""

from datetime import datetime
from typing import Any

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """
    Recolecta y calcula métricas de ejecución.
    
    Responsabilidades:
    - Calcular costos de LLM
    - Agregar métricas de tokens
    - Tracking de duración
    """
    
    def __init__(self):
        self._pricing_cache: dict[str, tuple[float, float]] = {}
    
    def calculate_cost(
        self,
        model_id: str,
        input_tokens: int | None,
        output_tokens: int | None,
        provider: str | None = None,
    ) -> float | None:
        """
        Calcula el costo de una llamada LLM.
        
        Args:
            model_id: ID del modelo (ej: "gpt-4o-mini")
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            provider: Proveedor opcional para key compuesta
            
        Returns:
            Costo en USD o None si no se puede calcular
        """
        if input_tokens is None and output_tokens is None:
            return None
        
        try:
            # Construir key para lookup
            key = f"{provider}:{model_id}" if provider else model_id
            
            # Obtener rates
            inp_rate = (
                settings.llm_pricing_input_per_1k_overrides.get(key)
                or settings.llm_pricing_input_per_1k.get(model_id)
                or 0.0
            )
            out_rate = (
                settings.llm_pricing_output_per_1k_overrides.get(key)
                or settings.llm_pricing_output_per_1k.get(model_id)
                or 0.0
            )
            
            # Calcular costo
            cost_input = (input_tokens or 0) / 1000.0 * inp_rate
            cost_output = (output_tokens or 0) / 1000.0 * out_rate
            
            return round(cost_input + cost_output, 6)
            
        except Exception as e:
            logger.debug(f"Error calculando costo: {e}")
            return None
    
    def aggregate_tokens(
        self,
        current: dict[str, int | None],
        new: dict[str, int | None],
    ) -> dict[str, int]:
        """
        Agrega tokens de múltiples llamadas.
        
        Args:
            current: Métricas actuales
            new: Nuevas métricas a agregar
            
        Returns:
            Métricas agregadas
        """
        return {
            "input_tokens": (current.get("input_tokens") or 0) + (new.get("input_tokens") or 0),
            "output_tokens": (current.get("output_tokens") or 0) + (new.get("output_tokens") or 0),
            "total_tokens": (current.get("total_tokens") or 0) + (new.get("total_tokens") or 0),
        }
    
    def calculate_duration_ms(
        self,
        started_at: datetime | None,
        completed_at: datetime | None = None,
    ) -> float | None:
        """
        Calcula la duración en milisegundos.
        
        Args:
            started_at: Timestamp de inicio
            completed_at: Timestamp de fin (default: ahora)
            
        Returns:
            Duración en ms o None
        """
        if started_at is None:
            return None
        
        end = completed_at or datetime.now()
        try:
            return (end - started_at).total_seconds() * 1000
        except Exception:
            return None
    
    def format_metrics_summary(
        self,
        tokens_total: int | None,
        cost_usd: float | None,
        duration_ms: float | None,
    ) -> str:
        """
        Formatea un resumen de métricas para logging.
        """
        parts = []
        
        if tokens_total is not None:
            parts.append(f"tok:{tokens_total}")
        
        if cost_usd is not None:
            parts.append(f"cost:${cost_usd:.6f}")
        
        if duration_ms is not None:
            parts.append(f"dur:{duration_ms:.0f}ms")
        
        return " | ".join(parts) if parts else "no metrics"
    
    def should_alert_duration(self, duration_ms: float | None) -> bool:
        """Verifica si la duración excede el umbral de alerta."""
        if not settings.alerts_enabled or duration_ms is None:
            return False
        return duration_ms > settings.alert_max_duration_ms
    
    def should_alert_tokens(self, total_tokens: int | None) -> bool:
        """Verifica si los tokens exceden el umbral de alerta."""
        if not settings.alerts_enabled or total_tokens is None:
            return False
        return total_tokens > settings.alert_max_total_tokens


# Instancia global
metrics_collector = MetricsCollector()
