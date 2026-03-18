"""
Gestor de buffer temporal para consolidación de mensajes.

Implementa la lógica del sistema de buffer de n8n:
- Push: Agrega mensajes al buffer en Redis
- Check: Verifica si debe procesar, esperar o ignorar
- Clear: Limpia el buffer después de procesar

El propósito es consolidar múltiples mensajes rápidos del usuario
en una sola respuesta, evitando respuestas fragmentadas.
"""

import asyncio
import json
from datetime import datetime
from typing import Literal

from src.config.settings import settings
from src.models.state import MessageData
from src.utils.logger import get_logger
from src.utils.redis_client import redis_client

logger = get_logger(__name__)

# Tipo para la acción del buffer
BufferAction = Literal["wait", "process", "duplicate", "skip"]


class BufferManager:
    """
    Gestiona el buffer temporal de mensajes en Redis.

    Replica la lógica del sistema de buffer de n8n:
    1. Cuando llega un mensaje, se agrega al buffer
    2. Se verifica el estado del buffer
    3. Si han pasado >10 segundos desde el último mensaje -> procesar
    4. Si no -> esperar y volver a verificar
    5. Si es duplicado -> ignorar

    Ejemplo de uso:
        buffer = BufferManager()

        # Agregar mensaje al buffer
        await buffer.add_message(identifier, message_data)

        # Verificar qué hacer
        action = await buffer.check_status(identifier, current_source_id)

        if action == "process":
            messages = await buffer.get_messages(identifier)
            # ... procesar mensajes ...
            await buffer.clear(identifier)
    """

    def __init__(self, wait_seconds: int | None = None):
        """
        Inicializa el gestor de buffer.

        Args:
            wait_seconds: Segundos a esperar antes de procesar
                         (default: settings.buffer_wait_seconds)
        """
        self.wait_seconds = wait_seconds or settings.buffer_wait_seconds
        self.buffer_ttl = 3600  # 1 hora de TTL para evitar memory leaks

    def _get_buffer_key(self, identifier: str) -> str:
        """
        Genera la clave Redis para el buffer de un usuario.

        Args:
            identifier: Identificador del usuario (ej: 'whatsapp:+58412XXXXXXX')

        Returns:
            Clave Redis (ej: 'buffer:whatsapp:+58412XXXXXXX')
        """
        return f"buffer:{identifier}"

    async def add_message(self, identifier: str, message: dict) -> int:
        """
        Agrega un mensaje al buffer del usuario.

        El mensaje se serializa a JSON y se agrega al final de la lista.

        Args:
            identifier: Identificador del usuario
            message: Diccionario con datos del mensaje

        Returns:
            Número de mensajes en el buffer después de agregar
        """
        key = self._get_buffer_key(identifier)

        # Serializar mensaje
        message_json = json.dumps(message, default=str)

        # Agregar al buffer
        count = await redis_client.push_to_list(key, message_json, self.buffer_ttl)

        logger.debug(
            "Mensaje agregado al buffer",
            identifier=identifier,
            buffer_count=count,
        )

        return count

    async def get_messages(self, identifier: str) -> list[MessageData]:
        """
        Obtiene todos los mensajes del buffer.

        Args:
            identifier: Identificador del usuario

        Returns:
            Lista de mensajes como objetos MessageData
        """
        key = self._get_buffer_key(identifier)

        # Obtener mensajes crudos
        raw_messages = await redis_client.get_list(key)

        return self._parse_messages(raw_messages)

    def _parse_messages(self, raw_messages: list[str]) -> list[MessageData]:
        """Parsea mensajes crudos a objetos MessageData."""
        messages = []
        for raw in raw_messages:
            try:
                data = json.loads(raw)
                messages.append(MessageData(**data))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "Error parseando mensaje del buffer",
                    error=str(e),
                    raw_message=raw[:100] if raw else "",
                )
        return messages

    async def claim_and_clear(self, identifier: str) -> list[MessageData]:
        """
        Operación atómica: obtiene mensajes y limpia el buffer.
        
        Usa un pipeline de Redis para garantizar que ningún mensaje
        se pierda entre la lectura y la eliminación.
        
        Esta es la forma SEGURA de obtener y limpiar el buffer.
        
        Args:
            identifier: Identificador del usuario
            
        Returns:
            Lista de mensajes reclamados
        """
        key = self._get_buffer_key(identifier)
        
        try:
            client = await redis_client.get_client()
            
            # Usar pipeline para operación atómica
            pipe = client.pipeline()
            pipe.lrange(key, 0, -1)  # Obtener todos los mensajes
            pipe.delete(key)          # Eliminar el buffer
            
            results = await pipe.execute()
            raw_messages = results[0] if results else []
            
            logger.debug(
                "Buffer reclamado y limpiado atómicamente",
                identifier=identifier,
                message_count=len(raw_messages),
            )
            
            return self._parse_messages(raw_messages)
            
        except Exception as e:
            logger.error(
                "Error en claim_and_clear, usando fallback",
                identifier=identifier,
                error=str(e),
            )
            # Fallback al método no-atómico en caso de error
            messages = await self.get_messages(identifier)
            await self.clear(identifier)
            return messages

    async def get_messages_legacy(self, identifier: str) -> list[MessageData]:
        """
        Método legacy: obtiene mensajes SIN limpiar.
        
        ADVERTENCIA: Este método puede causar race conditions si se usa
        seguido de clear(). Usar claim_and_clear() en su lugar.
        """
        key = self._get_buffer_key(identifier)
        raw_messages = await redis_client.get_list(key)
        
        # Parsear a MessageData
        messages = []
        for raw in raw_messages:
            try:
                data = json.loads(raw)
                messages.append(MessageData(**data))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "Error parseando mensaje del buffer",
                    error=str(e),
                    raw_message=raw[:100],
                )

        return messages

    async def check_status(self, identifier: str, current_source_id: str) -> BufferAction:
        """
        Determina qué acción tomar con el buffer.

        Implementa la lógica del Switch de n8n:

        1. DUPLICATE: El primer mensaje del buffer tiene un source_id diferente
           al mensaje actual (ya fue procesado)

        2. WAIT: El último mensaje fue hace menos de wait_seconds
           (el usuario sigue escribiendo)

        3. PROCESS: Han pasado más de wait_seconds desde el último mensaje
           (listo para procesar)

        Args:
            identifier: Identificador del usuario
            current_source_id: source_id del mensaje que disparó el webhook

        Returns:
            BufferAction: "duplicate", "wait", "process" o "skip"
        """
        messages = await self.get_messages(identifier)

        if not messages:
            logger.debug("Buffer vacío", identifier=identifier)
            return "skip"

        # CASO 1: Verificar duplicado
        # Si el último mensaje del buffer no coincide con el actual,
        # se trata de un webhook fuera de orden o ya procesado
        last_message = messages[-1]
        if last_message.source_id != current_source_id:
            logger.debug(
                "Mensaje duplicado detectado",
                identifier=identifier,
                last_source_id=last_message.source_id,
                current_source_id=current_source_id,
            )
            return "duplicate"

        # CASO 2 vs 3: Verificar tiempo desde último mensaje

        try:
            # Parsear timestamp
            last_timestamp = datetime.fromisoformat(last_message.created_at.replace("Z", "+00:00"))

            # Calcular diferencia
            now = datetime.now(last_timestamp.tzinfo)
            time_diff = now - last_timestamp

            if time_diff.total_seconds() < self.wait_seconds:
                logger.debug(
                    "Usuario sigue escribiendo",
                    identifier=identifier,
                    seconds_since_last=time_diff.total_seconds(),
                    wait_seconds=self.wait_seconds,
                )
                return "wait"

        except (ValueError, TypeError) as e:
            logger.warning(
                "Error parseando timestamp, procesando de todas formas",
                error=str(e),
                created_at=last_message.created_at,
            )

        # CASO 3: Listo para procesar
        logger.info(
            "Buffer listo para procesar",
            identifier=identifier,
            message_count=len(messages),
        )
        return "process"

    async def clear(self, identifier: str) -> bool:
        """
        Limpia el buffer del usuario.

        Debe llamarse después de procesar los mensajes.

        Args:
            identifier: Identificador del usuario

        Returns:
            True si se eliminó el buffer
        """
        key = self._get_buffer_key(identifier)
        result = await redis_client.delete_key(key)

        logger.debug("Buffer limpiado", identifier=identifier, deleted=result)

        return result

    async def wait_and_check(
        self,
        identifier: str,
        current_source_id: str,
        max_iterations: int = 3,
    ) -> tuple[BufferAction, list[MessageData]]:
        """
        Repite verificación del buffer con pequeñas esperas hasta decidir.

        Args:
            identifier: Identificador del usuario
            current_source_id: source_id del mensaje actual
            max_iterations: Máximo de intentos de verificación

        Returns:
            Tupla (acción, mensajes). Si acción es "process" retorna los mensajes,
            de lo contrario retorna lista vacía.
        """
        attempts = 0
        while attempts < max_iterations:
            action = await self.check_status(identifier, current_source_id)
            if action == "wait":
                # Esperar un pequeño intervalo antes de reintentar
                await asyncio.sleep(self.wait_seconds)
                attempts += 1
                continue
            if action == "process":
                msgs = await self.get_messages(identifier)
                return action, msgs
            if action in ("duplicate", "skip"):
                return action, []
        # Si agotó intentos sin entrar en "process", decidir por última vez
        final_action = await self.check_status(identifier, current_source_id)
        if final_action == "process":
            msgs = await self.get_messages(identifier)
            return final_action, msgs
        return final_action, []



# Instancia global
buffer_manager = BufferManager()
