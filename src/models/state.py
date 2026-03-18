"""
Estado del grafo LangGraph.

Define el estado tipado que fluye entre todos los nodos del grafo.
Este es el corazón de LangGraph - un TypedDict que contiene toda la información
necesaria para procesar un mensaje de principio a fin.

Cada nodo del grafo recibe este estado, lo modifica y lo retorna.
"""

from datetime import datetime
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageData(BaseModel):
    """
    Representa un mensaje procesado del buffer.

    Attributes:
        content: Contenido del mensaje (texto o transcripción)
        content_type: Tipo de contenido original (text, audio, image)
        source_id: ID único del mensaje en Chatwoot
        created_at: Timestamp ISO del mensaje
        attachments: Lista de adjuntos (opcional)
        info_imagen: Descripción de la imagen analizada con Vision (opcional)
    """

    content: str = Field(default="", description="Contenido textual del mensaje")
    content_type: Literal["text", "audio", "image"] = Field(
        default="text", description="Tipo de contenido del mensaje"
    )
    source_id: str = Field(default="", description="ID único del mensaje")
    created_at: str = Field(default="", description="Timestamp ISO del mensaje")
    attachments: list[dict] | None = Field(
        default=None, description="Lista de adjuntos del mensaje"
    )
    info_imagen: str | None = Field(default=None, description="Análisis de imagen por GPT-4 Vision")

    model_config = ConfigDict(extra="allow")

    @field_validator("created_at", mode="before")
    @classmethod
    def _normalize_created_at(cls, v):
        if isinstance(v, (int, float)):
            try:
                ts = int(v)
                return datetime.utcfromtimestamp(ts).isoformat() + "Z"
            except Exception:
                return str(v)
        return v if isinstance(v, str) else ""


class ChatbotState(TypedDict, total=False):
    """
    Estado del grafo LangGraph para el chatbot.

    Este TypedDict define todos los campos que pueden existir en el estado.
    Cada nodo del grafo puede leer y modificar estos campos.

    El estado se divide en secciones lógicas:
    - Datos de entrada (raw_payload, event_type)
    - Datos del usuario (identifier, phone_number, etc.)
    - Buffer y procesamiento (buffer_messages, processed_messages)
    - Contexto para IA (chat_input, info_imagen)
    - Respuesta (ai_response, formatted_parts)
    - Escalamiento (needs_escalation, escalation_reason)
    - Control de flujo (error, should_continue)

    Ejemplo de uso en un nodo:
        def my_node(state: ChatbotState) -> ChatbotState:
            # Leer del estado
            messages = state.get("buffer_messages", [])

            # Modificar el estado
            state["processed_messages"] = process(messages)

            return state
    """

    # =========================================================================
    # ENTRADA - Datos crudos del webhook
    # =========================================================================
    raw_payload: dict
    """Payload completo del webhook de entrada."""

    event_type: str
    """Tipo de evento (message_created, etc.)."""

    # =========================================================================
    # USUARIO - Datos extraídos del mensaje
    # =========================================================================
    identifier: str
    """Identificador único del usuario (ej: 'whatsapp:+58412XXXXXXX')."""

    phone_number: str
    """Número de teléfono del usuario."""

    user_name: str
    """Nombre del usuario."""

    account_id: int
    """ID de la cuenta en el sistema origen (si aplica)."""

    conversation_id: int
    """ID de la conversación en el sistema origen (si aplica)."""

    contact_id: int
    """ID del contacto en el sistema origen (si aplica)."""

    sender_type: str
    """Tipo de remitente ('Contact' o 'User')."""

    bot_state: str
    """Estado del bot para este usuario ('ON' u 'OFF')."""

    tenant_id: str
    tenant_slug: str
    namespaced_id: str

    # =========================================================================
    # BUFFER - Sistema de consolidación de mensajes
    # =========================================================================
    current_message: dict
    """Mensaje actual que disparó el webhook."""

    buffer_messages: list[MessageData]
    """Lista de mensajes en el buffer."""

    buffer_action: Literal["wait", "process", "duplicate", "skip"]
    """Acción determinada por el sistema de buffer."""

    # =========================================================================
    # PROCESAMIENTO - Resultados del procesamiento multimodal
    # =========================================================================
    processed_messages: list[MessageData]
    """Mensajes después del procesamiento multimodal."""

    # =========================================================================
    # CONTEXTO IA - Input para el agente
    # =========================================================================
    chat_input: str
    """Mensajes consolidados como texto para el agente."""

    info_imagen: str | None
    """Análisis de imágenes consolidado (opcional)."""

    # =========================================================================
    # CONFIGURACIÓN IA - Prompt y parámetros por tenant
    # =========================================================================
    vertical_id: str
    """ID del nicho/vertical (ej: restaurante, optica)."""

    tenant_data: dict
    """Datos operativos específicos de la empresa."""

    system_prompt: str
    temperature: float | None
    max_tokens: int | None

    # =========================================================================
    # RESPUESTA - Output del agente
    # =========================================================================
    ai_response: str
    """Respuesta cruda generada por el agente."""

    formatted_parts: list[str]
    """Respuesta dividida en partes [part_1, part_2, part_3]."""

    # =========================================================================
    # ESCALAMIENTO - Detección de necesidad de humano
    # =========================================================================
    needs_escalation: bool
    """Si la conversación requiere atención humana."""

    escalation_reason: str | None
    """Razón del escalamiento (opcional)."""

    # =========================================================================
    # CONTROL DE FLUJO - Manejo de errores y continuación
    # =========================================================================
    error: str | None
    """Mensaje de error si ocurrió alguno."""

    should_continue: bool
    """Si el flujo debe continuar al siguiente nodo."""

    _execution_id: str
    _trace_id: str
    _sandbox_mode: bool

    _node_metrics: dict[str, Any]

    _outbound_response: dict[str, Any]

    actions: dict[str, Any]
    nlu: dict[str, Any]
    outbound_message_parts: list[str]
    outbound_conversation_id: int

    crm_memory: list[dict[str, str]]
    rag_docs: list[dict[str, str]]
    google_sheet_id: str
    inventory_query: str | None
    sheets_result: dict | None
    knowledge_plan: dict[str, Any]
    gating_stop: bool
    gating_escalate: bool


def create_initial_state(payload: dict) -> ChatbotState:
    """
    Crea el estado inicial del grafo a partir del payload del webhook.

    Args:
        payload: Payload crudo del webhook de entrada

    Returns:
        ChatbotState inicializado con valores por defecto
    """
    return ChatbotState(
        raw_payload=payload,
        event_type="",
        identifier="",
        phone_number="",
        user_name="",
        account_id=0,
        conversation_id=0,
        contact_id=0,
        sender_type="",
        bot_state="ON",
        tenant_id="",
        tenant_slug="",
        namespaced_id="",
        current_message={},
        buffer_messages=[],
        buffer_action="skip",
        processed_messages=[],
        chat_input="",
        info_imagen=None,
        system_prompt="",
        temperature=None,
        max_tokens=None,
        ai_response="",
        formatted_parts=[],
        needs_escalation=False,
        escalation_reason=None,
        error=None,
        should_continue=True,
        _trace_id="",
        vertical_id="restaurante",
        tenant_data={},
        crm_memory=[],
        rag_docs=[],
        google_sheet_id="",
        inventory_query=None,
        sheets_result=None,
        knowledge_plan={},
        gating_stop=False,
        gating_escalate=False,
        actions={},
    )
