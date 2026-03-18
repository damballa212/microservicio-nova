"""
Módulo de buffer.

Implementa el sistema de consolidación de mensajes similar al workflow de n8n.
Espera 10 segundos antes de procesar para agrupar mensajes rápidos.
"""

from src.buffer.buffer_manager import BufferManager

__all__ = ["BufferManager"]
