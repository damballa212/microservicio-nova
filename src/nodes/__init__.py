"""
Módulo de nodos LangGraph.

Contiene todos los nodos del grafo del chatbot.
Cada nodo es una función que recibe el estado y lo modifica.
"""

from src.nodes.ai_agent import generate_response
from src.nodes.buffer import (
    add_to_buffer,
    check_buffer_status,
    route_buffer_decision,
    wait_for_messages,
)
from src.nodes.escalation import (
    classify_escalation,
    escalate_to_human,
    route_escalation,
)
from src.nodes.formatter import format_response
from src.nodes.knowledge import (
    lookup_inventory_sheets,
    merge_knowledge,
    plan_knowledge,
    retrieve_docs_rag,
)
from src.nodes.multimodal import process_multimodal
from src.nodes.outbound_webhook import post_to_outbound_webhook
from src.nodes.validation import (
    check_bot_state,
    extract_message_data,
    route_after_bot_check,
    route_after_event_validation,
    route_after_sender_validation,
    validate_event,
    validate_sender,
)

__all__ = [
    # Validation
    "validate_event",
    "validate_sender",
    "check_bot_state",
    "extract_message_data",
    "route_after_event_validation",
    "route_after_sender_validation",
    "route_after_bot_check",
    # Buffer
    "add_to_buffer",
    "check_buffer_status",
    "wait_for_messages",
    "route_buffer_decision",
    # Processing
    "process_multimodal",
    # Knowledge
    "plan_knowledge",
    "lookup_inventory_sheets",
    "retrieve_docs_rag",
    "merge_knowledge",
    # AI
    "generate_response",
    "format_response",
    # Output
    "post_to_outbound_webhook",
    # Escalation
    "classify_escalation",
    "escalate_to_human",
    "route_escalation",
]
