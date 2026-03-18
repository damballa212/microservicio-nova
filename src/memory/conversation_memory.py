"""
Memoria conversacional persistente en Redis.

Mantiene el historial de los últimos N mensajes por usuario.
Similar al ConversationBufferWindowMemory de LangChain pero
con persistencia en Redis.
"""

import json
from typing import Any

from src.config.settings import settings
from src.utils.logger import get_logger
from src.utils.redis_client import redis_client

PERSISTENT_MEMORY_ENABLED: bool = False
persistent_memory: Any | None = None

# Import persistent memory for permanent storage
try:
    from src.memory.persistent_memory import persistent_memory as _pm
    persistent_memory = _pm
    PERSISTENT_MEMORY_ENABLED = True
except Exception as e:
    logger = get_logger(__name__)
    logger.warning("Persistent memory not available, using Redis only", error=str(e))
    PERSISTENT_MEMORY_ENABLED = False

logger = get_logger(__name__)


class ConversationMemory:
    """
    Gestor de memoria conversacional.

    Almacena el historial de conversaciones en Redis con:
    - TTL de 24 horas (configurable)
    - Ventana de N mensajes (configurable)
    - Persistencia entre reinicios

    Ejemplo:
        memory = ConversationMemory()

        # Agregar mensajes
        await memory.add_message("user123", "user", "Hola")
        await memory.add_message("user123", "assistant", "Hola! ¿Cómo te puedo ayudar?")

        # Obtener historial
        history = await memory.get_history("user123")
        # [{"role": "user", "content": "Hola"}, {"role": "assistant", "content": "..."}]
    """

    def __init__(
        self,
        window_size: int | None = None,
        ttl_hours: int = 24,
    ):
        """
        Inicializa la memoria conversacional.

        Args:
            window_size: Número de mensajes a mantener (default: settings)
            ttl_hours: Horas de vida del historial
        """
        self.window_size = window_size or settings.memory_window_size
        self.ttl = ttl_hours * 3600  # Convertir a segundos

    def _get_key(self, identifier: str) -> str:
        """Genera la clave Redis para un usuario."""
        return f"memory:{identifier}"

    async def add_message(
        self,
        identifier: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Agrega un mensaje al historial.

        Guarda en:
        1. PostgreSQL (permanente) si está disponible
        2. Redis (caché rápido)

        Args:
            identifier: Identificador del usuario
            role: Rol del mensaje ("user" o "assistant")
            content: Contenido del mensaje
            metadata: Metadatos opcionales (tokens, modelo, etc.)
        """
        key = self._get_key(identifier)

        message = {
            "role": role,
            "content": content,
        }

        # Guardar en PostgreSQL (permanente)
        if PERSISTENT_MEMORY_ENABLED and persistent_memory:
            try:
                await persistent_memory.save_message(
                    identifier=identifier,
                    role=role,
                    content=content,
                    metadata=metadata or {},
                )
            except Exception as e:
                logger.error(
                    "Failed to save to persistent storage",
                    identifier=identifier,
                    error=str(e),
                )

        # Guardar en Redis (caché)
        message_json = json.dumps(message)
        await redis_client.push_to_list(key, message_json, self.ttl)

        # Recortar a window_size * 2 (user + assistant por turno)
        await self._trim_history(identifier)

        logger.debug(
            "Mensaje agregado a memoria",
            identifier=identifier,
            role=role,
            content_length=len(content),
            persistent=PERSISTENT_MEMORY_ENABLED,
        )

    async def _trim_history(self, identifier: str) -> None:
        """
        Recorta el historial al tamaño de ventana.

        Mantiene solo los últimos window_size * 2 mensajes.
        """
        key = self._get_key(identifier)
        client = await redis_client.get_client()

        # Obtener longitud actual
        length = await client.llen(key)
        max_length = self.window_size * 2

        if length > max_length:
            # Recortar desde el inicio
            await client.ltrim(key, length - max_length, -1)
            logger.debug(
                "Historial recortado",
                identifier=identifier,
                old_length=length,
                new_length=max_length,
            )

    async def get_history(
        self,
        identifier: str,
        from_persistent: bool = False,
    ) -> list[dict[str, str]]:
        """
        Obtiene el historial de conversación.

        Estrategia:
        1. Intenta leer de Redis (rápido)
        2. Si Redis está vacío y persistent memory disponible, reconstruye desde PostgreSQL

        Args:
            identifier: Identificador del usuario
            from_persistent: Si True, fuerza lectura desde PostgreSQL

        Returns:
            Lista de mensajes como {"role": str, "content": str}
        """
        key = self._get_key(identifier)

        # Si se solicita explícitamente de persistent storage
        if from_persistent and PERSISTENT_MEMORY_ENABLED and persistent_memory:
            try:
                pg_messages = await persistent_memory.load_history(
                    identifier=identifier,
                    limit=self.window_size * 2,
                )
                return [{"role": m["role"], "content": m["content"]} for m in pg_messages]
            except Exception as e:
                logger.error("Failed to load from persistent storage", error=str(e))

        # Intentar leer de Redis primero
        raw_messages = await redis_client.get_list(key)

        messages = []
        for raw in raw_messages:
            try:
                messages.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

        # Si Redis está vacío pero tenemos persistent memory, reconstruir
        if not messages and PERSISTENT_MEMORY_ENABLED and persistent_memory:
            try:
                logger.info(
                    "Redis cache empty, rebuilding from persistent storage",
                    identifier=identifier,
                )
                pg_messages = await persistent_memory.load_history(
                    identifier=identifier,
                    limit=self.window_size * 2,
                )

                # Reconstruir cache de Redis
                for msg in pg_messages:
                    message_json = json.dumps({"role": msg["role"], "content": msg["content"]})
                    await redis_client.push_to_list(key, message_json, self.ttl)

                messages = [{"role": m["role"], "content": m["content"]} for m in pg_messages]

                logger.info(
                    "Rebuilt Redis cache from persistent storage",
                    identifier=identifier,
                    message_count=len(messages),
                )
            except Exception as e:
                logger.error(
                    "Failed to rebuild from persistent storage",
                    identifier=identifier,
                    error=str(e),
                )

        return messages

    async def clear_history(self, identifier: str) -> bool:
        """
        Limpia el historial de un usuario.

        Args:
            identifier: Identificador del usuario

        Returns:
            True si se eliminó
        """
        key = self._get_key(identifier)
        result = await redis_client.delete_key(key)

        logger.info("Historial limpiado", identifier=identifier)

        return result

    async def get_formatted_history(
        self,
        identifier: str,
    ) -> str:
        """
        Obtiene el historial formateado como texto.

        Útil para inyectar en prompts.

        Args:
            identifier: Identificador del usuario

        Returns:
            Historial como texto formateado
        """
        history = await self.get_history(identifier)

        lines = []
        for msg in history:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            lines.append(f"{role}: {msg['content']}")

        return "\n".join(lines)


# Instancia global
conversation_memory = ConversationMemory()
