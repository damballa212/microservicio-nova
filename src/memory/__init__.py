"""
Módulo de memoria conversacional.

Gestiona el historial de conversaciones por usuario en Redis.
"""

from src.memory.conversation_memory import ConversationMemory, conversation_memory

__all__ = ["ConversationMemory", "conversation_memory"]
