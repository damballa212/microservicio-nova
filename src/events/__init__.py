"""
Módulo de eventos para el dashboard.

Sistema de broadcast de eventos para visualización en tiempo real.
"""

from src.events.emitter import EventEmitter, event_emitter
from src.events.models import ExecutionEvent, NodeStatus

__all__ = ["EventEmitter", "event_emitter", "ExecutionEvent", "NodeStatus"]
