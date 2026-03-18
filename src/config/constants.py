"""
Constantes y Enums del sistema.

Centraliza todas las constantes, magic strings y enums
utilizados a lo largo del código para evitar typos y
facilitar refactorizaciones.
"""

from enum import Enum, auto
from typing import Literal


# === ESTADOS DEL BOT ===

class BotState(str, Enum):
    """Estados posibles del bot para un usuario."""
    ON = "ON"
    OFF = "OFF"
    PAUSED = "PAUSED"  # Para mantenimiento
    
    @classmethod
    def is_active(cls, state: str) -> bool:
        """Verifica si el estado indica que el bot está activo."""
        return state.upper() == cls.ON.value


# === TIPOS DE EVENTO ===

class EventType(str, Enum):
    """Tipos de eventos de webhook."""
    MESSAGE_CREATED = "message_created"
    MESSAGE_UPDATED = "message_updated"
    CONVERSATION_CREATED = "conversation_created"
    CONVERSATION_UPDATED = "conversation_updated"


# === TIPOS DE SENDER ===

class SenderType(str, Enum):
    """Tipos de remitente de mensaje."""
    CONTACT = "Contact"
    USER = "User"  # Agente humano
    BOT = "Bot"


# === ACCIONES DEL BUFFER ===

# Ya existe BufferAction en buffer_manager.py, pero lo reexportamos aquí
BufferAction = Literal["wait", "process", "duplicate", "skip"]


class BufferActionEnum(str, Enum):
    """Acciones posibles para el buffer de mensajes."""
    WAIT = "wait"
    PROCESS = "process"
    DUPLICATE = "duplicate"
    SKIP = "skip"


# === ESCALAMIENTO ===

class EscalationReason(str, Enum):
    """Razones para escalar a humano."""
    USER_REQUEST = "user_request"
    COMPLEXITY = "complexity"
    SENTIMENT_NEGATIVE = "sentiment_negative"
    MODEL_FLAGGED = "model_flagged"
    CRM_FORCED = "crm_forced"


class EscalationResponse(str, Enum):
    """Respuestas del clasificador de escalamiento."""
    YES = "SI"
    NO = "NO"
    
    @classmethod
    def requires_human(cls, response: str) -> bool:
        """Verifica si la respuesta indica escalamiento."""
        clean = response.strip().upper()
        return clean in ("SI", "SÍ", "YES", "TRUE", "1")


# === INTENCIONES COMUNES ===

class CommonIntent(str, Enum):
    """Intenciones comunes detectadas por NLU."""
    GREETING = "saludo"
    GOODBYE = "despedida"
    THANKS = "agradecimiento"
    MENU_QUERY = "menu_consulta"
    PRICE_QUERY = "precio_consulta"
    RESERVATION = "reserva"
    ORDER = "pedido"
    COMPLAINT = "reclamo"
    HUMAN_REQUEST = "solicita_humano"
    UNKNOWN = "unknown"


# === VERTICALES SOPORTADAS ===

class Vertical(str, Enum):
    """Verticales/nichos soportados."""
    RESTAURANT = "restaurante"
    ECOMMERCE = "ecommerce"
    OPTICS = "optica"
    DEFAULT = "restaurante"


# === PROVEEDORES LLM ===

class LLMProvider(str, Enum):
    """Proveedores de LLM soportados."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GOOGLE = "google"


# === TIPOS DE CONTENIDO ===

class ContentType(str, Enum):
    """Tipos de contenido de mensaje."""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"


# === ESTADOS DE NODO (para eventos) ===

class NodeStatus(str, Enum):
    """Estados de ejecución de un nodo."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


# === CONSTANTES NUMÉRICAS ===

class Limits:
    """Límites y valores por defecto."""
    MAX_MESSAGE_LENGTH = 4096
    MAX_PARTS_WHATSAPP = 3
    MAX_CHARS_PER_PART = 500
    DEFAULT_BUFFER_TTL_SECONDS = 3600
    DEFAULT_MEMORY_WINDOW = 10
    MAX_RAG_DOCS = 5
    MAX_CRM_MESSAGES = 10


# === KEYS DE REDIS ===

class RedisKeyPrefix:
    """Prefijos de claves Redis."""
    BUFFER = "buffer:"
    MEMORY = "memory:"
    METRICS = "metrics:"
    EXECUTION = "metrics:execution:"
    LOGS = "metrics:logs:"
    EVENTS = "events:"


# === MENSAJES DE ERROR ESTÁNDAR ===

class ErrorMessages:
    """Mensajes de error estándar para el usuario."""
    GENERIC = "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."
    NO_INPUT = "Lo siento, no pude procesar tu mensaje."
    PARSING_FAILED = "Lo siento, tuve un problema procesando mi respuesta."
    ESCALATION = "Te voy a pasar con uno de nuestros asesores para ayudarte mejor."


# === MENSAJES DE ESCALAMIENTO ===

class EscalationMessages:
    """Mensajes cuando se escala a humano."""
    DEFAULT = "Te voy a pasar con uno de nuestros asesores para ayudarte mejor."
    COMPLEX_QUERY = "Tu consulta requiere atención especial. Te paso con un asesor."
    USER_REQUESTED = "Claro, te comunico con uno de nuestros asesores."
    SENTIMENT = "Entiendo tu frustración. Te paso con un asesor para resolver esto."
