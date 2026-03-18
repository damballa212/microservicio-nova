"""
Cliente Redis singleton.

Proporciona una conexión Redis reutilizable para todo el proyecto.
Se usa para el sistema de buffer y la memoria conversacional.
"""

from typing import cast

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Pool de conexiones global
_connection_pool: ConnectionPool | None = None


def get_connection_pool() -> ConnectionPool:
    """
    Obtiene o crea el pool de conexiones Redis.

    Returns:
        Pool de conexiones compartido
    """
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=10,
            decode_responses=True,
        )
        logger.info("Pool de conexiones Redis creado", url=settings.redis_url)
    return _connection_pool


async def get_redis_client() -> redis.Redis:
    """
    Obtiene una conexión Redis del pool.

    Returns:
        Cliente Redis async

    Ejemplo:
        client = await get_redis_client()
        await client.set("key", "value")
    """
    pool = get_connection_pool()
    return redis.Redis(connection_pool=pool)


class RedisClient:
    """
    Wrapper singleton para el cliente Redis.

    Proporciona métodos de conveniencia para operaciones comunes.
    """

    def __init__(self):
        self._client: redis.Redis | None = None

    async def get_client(self) -> redis.Redis:
        """Obtiene el cliente Redis (lazy initialization)."""
        if self._client is None:
            self._client = await get_redis_client()
        return self._client

    async def close(self) -> None:
        """Cierra la conexión Redis."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Conexión Redis cerrada")

    # === Operaciones de Buffer ===

    async def push_to_list(self, key: str, value: str, ttl: int = 3600) -> int:
        """
        Agrega un valor al final de una lista.

        Args:
            key: Clave de la lista
            value: Valor a agregar
            ttl: Tiempo de vida en segundos (default: 1 hora)

        Returns:
            Longitud de la lista después de agregar
        """
        client = await self.get_client()
        length = await client.rpush(key, value)
        await client.expire(key, ttl)
        return length

    async def get_list(self, key: str) -> list[str]:
        """
        Obtiene todos los elementos de una lista.

        Args:
            key: Clave de la lista

        Returns:
            Lista de valores
        """
        client = await self.get_client()
        return await client.lrange(key, 0, -1)

    async def delete_key(self, key: str) -> bool:
        """
        Elimina una clave.

        Args:
            key: Clave a eliminar

        Returns:
            True si se eliminó, False si no existía
        """
        client = await self.get_client()
        result = await client.delete(key)
        return result > 0

    # === Operaciones de Memoria ===

    async def set_with_ttl(self, key: str, value: str, ttl: int = 3600) -> bool:
        """
        Establece un valor con tiempo de vida.

        Args:
            key: Clave
            value: Valor
            ttl: Tiempo de vida en segundos

        Returns:
            True si se estableció correctamente
        """
        client = await self.get_client()
        return await client.setex(key, ttl, value)

    async def set_value(self, key: str, value: str) -> bool:
        client = await self.get_client()
        return bool(await client.set(key, value))

    async def get_value(self, key: str) -> str | None:
        """
        Obtiene un valor por clave.

        Args:
            key: Clave

        Returns:
            Valor o None si no existe
        """
        client = await self.get_client()
        return await client.get(key)

    async def exists(self, key: str) -> bool:
        """
        Verifica si una clave existe.

        Args:
            key: Clave a verificar

        Returns:
            True si existe
        """
        client = await self.get_client()
        return await client.exists(key) > 0

    async def publish_json(self, channel: str, payload: dict) -> int:
        client = await self.get_client()
        try:
            body = __import__("json").dumps(payload, ensure_ascii=False)
        except Exception:
            body = str(payload)
        return await client.publish(channel, body)

    async def get_pubsub(self):
        client = await self.get_client()
        return client.pubsub()

    async def stream_add(
        self, stream: str, fields: dict[str, str], maxlen: int | None = None
    ) -> str:
        client = await self.get_client()
        if maxlen is not None:
            return cast(str, await client.xadd(stream, fields, maxlen=maxlen, approximate=True))
        return cast(str, await client.xadd(stream, fields))

    async def stream_len(self, stream: str) -> int:
        client = await self.get_client()
        return await client.xlen(stream)

    async def stream_group_create(self, stream: str, group: str) -> None:
        client = await self.get_client()
        try:
            await client.xgroup_create(stream, group, id="0-0", mkstream=True)
        except Exception as e:
            msg = str(e)
            if "BUSYGROUP" in msg or "already exists" in msg:
                return
            raise

    async def stream_read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 1,
        block_ms: int = 5000,
    ):
        client = await self.get_client()
        return await client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )

    async def stream_ack(self, stream: str, group: str, message_id: str) -> int:
        client = await self.get_client()
        return int(await client.xack(stream, group, message_id))

    async def stream_info_consumers(self, stream: str, group: str):
        client = await self.get_client()
        return await client.xinfo_consumers(stream, group)

    async def stream_pending_summary(self, stream: str, group: str):
        client = await self.get_client()
        return await client.xpending(stream, group)


# Instancia global del cliente
redis_client = RedisClient()
