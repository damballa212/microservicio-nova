"""
Modelos de eventos para el dashboard.

Define la estructura de los eventos emitidos durante la ejecución del grafo.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    """Estado de un nodo en el grafo."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


class NodeEvent(BaseModel):
    """Evento de un nodo individual."""

    node_name: str = Field(description="Nombre del nodo")
    status: NodeStatus = Field(description="Estado del nodo")
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_ms: float | None = Field(default=None)
    error: str | None = Field(default=None)
    output_preview: str | None = Field(default=None, description="Vista previa del output")
    provider: str | None = Field(default=None)
    model_id: str | None = Field(default=None)
    input_tokens: int | None = Field(default=None)
    output_tokens: int | None = Field(default=None)
    total_tokens: int | None = Field(default=None)
    cost_usd: float | None = Field(default=None)


class ExecutionEvent(BaseModel):
    """Evento de ejecución completa del grafo."""

    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = Field(default=None)
    status: NodeStatus = Field(default=NodeStatus.PENDING)

    # Datos del mensaje
    identifier: str = Field(default="")
    user_name: str = Field(default="")
    conversation_id: int = Field(default=0)
    chat_input: str = Field(default="")

    # Estado de nodos
    nodes: dict[str, NodeEvent] = Field(default_factory=dict)
    current_node: str | None = Field(default=None)

    # Resultado
    ai_response: str | None = Field(default=None)
    error: str | None = Field(default=None)
    input_tokens_total: int | None = Field(default=None)
    output_tokens_total: int | None = Field(default=None)
    total_tokens_total: int | None = Field(default=None)
    cost_usd_total: float | None = Field(default=None)
    logs: list[dict] = Field(default_factory=list)
    payload_in_preview: str | None = Field(default=None)
    payload_out_preview: str | None = Field(default=None)

    def to_broadcast(self) -> dict:
        """Convierte el evento a formato para broadcast."""
        return {
            "type": "execution_update",
            "data": self.model_dump(mode="json"),
        }


class GraphDefinition(BaseModel):
    """Definición del grafo para visualización."""

    nodes: list[str] = Field(description="Lista de nodos")
    edges: list[dict[str, str]] = Field(description="Lista de edges {'from': ..., 'to': ...}")

    @classmethod
    def from_chatbot_graph(cls) -> "GraphDefinition":
        """Genera la definición desde el grafo del chatbot."""
        nodes = [
            "validate_event",
            "validate_sender",
            "check_bot_state",
            "extract_data",
            "add_to_buffer",
            "check_buffer_status",
            "wait_for_messages",
            "process_multimodal",
            "generate_response",
            "format_response",
            "post_to_outbound_webhook",
            "classify_escalation",
            "escalate_to_human",
        ]

        edges = [
            {"from": "validate_event", "to": "validate_sender"},
            {"from": "validate_sender", "to": "check_bot_state"},
            {"from": "check_bot_state", "to": "extract_data"},
            {"from": "extract_data", "to": "add_to_buffer"},
            {"from": "add_to_buffer", "to": "check_buffer_status"},
            {"from": "check_buffer_status", "to": "wait_for_messages", "condition": "wait"},
            {"from": "check_buffer_status", "to": "process_multimodal", "condition": "process"},
            {"from": "wait_for_messages", "to": "check_buffer_status"},
            {"from": "process_multimodal", "to": "generate_response"},
            {"from": "generate_response", "to": "format_response"},
            {"from": "format_response", "to": "post_to_outbound_webhook"},
            {"from": "post_to_outbound_webhook", "to": "classify_escalation"},
            {"from": "classify_escalation", "to": "escalate_to_human", "condition": "escalate"},
        ]

        return cls(nodes=nodes, edges=edges)
