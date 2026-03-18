"""
Tests para los nodos de validación.
"""

import pytest

from src.api.router import _normalize_inbound_payload
from src.models.state import create_initial_state
from src.nodes.validation import (
    check_bot_state,
    extract_message_data,
    route_after_bot_check,
    route_after_event_validation,
    validate_event,
    validate_sender,
)

# === Fixtures ===


@pytest.fixture
def valid_webhook_payload():
    """Payload válido de webhook de Chatwoot."""
    return {
        "body": {
            "event": "message_created",
            "conversation": {
                "messages": [
                    {
                        "content": "Hola, necesito ayuda",
                        "account_id": 2,
                        "conversation_id": 123,
                        "source_id": "wamid.abc123",
                        "content_type": "text",
                        "created_at": "2024-01-15T10:00:00Z",
                        "sender_type": "Contact",
                        "sender": {
                            "identifier": "whatsapp:+58412XXXXXXX",
                            "phone_number": "+58412XXXXXXX",
                            "name": "Cliente Test",
                            "custom_attributes": {"estado": "ON"},
                        },
                        "attachments": [],
                    }
                ],
                "contact_inbox": {"contact_id": 456},
            },
        }
    }


@pytest.fixture
def agent_message_payload():
    """Payload de mensaje de agente (no debe procesarse)."""
    return {
        "body": {
            "event": "message_created",
            "conversation": {
                "messages": [
                    {"content": "Respuesta del agente", "sender_type": "User", "sender": {}}
                ]
            },
        }
    }


@pytest.fixture
def bot_off_payload():
    """Payload con bot desactivado."""
    return {
        "body": {
            "event": "message_created",
            "conversation": {
                "messages": [
                    {
                        "content": "Mensaje",
                        "sender_type": "Contact",
                        "sender": {"custom_attributes": {"estado": "OFF"}},
                    }
                ]
            },
        }
    }


@pytest.fixture
def flowify_wrapper_payload_minimal():
    return {
        "empresa_id": 10,
        "empresa_slug": "acme",
        "schema_version": "1.0",
        "trace_id": "trace_test",
        "idempotency_key": "chatwoot:account:2:conv:123:msg:wamid.abc123",
        "timestamp_received": "2024-01-15T10:00:01Z",
        "gating": {"stop_processing": False, "force_escalation": True},
        "memoria_conversacional": [
            {"role": "user", "content": "Hola", "timestamp": "2024-01-15T09:59:00Z"},
            {"role": "assistant", "content": "Hola!", "timestamp": "2024-01-15T09:59:05Z"},
        ],
        "chatwoot_payload": {
            "event": "message_created",
            "message_type": "incoming",
            "account": {"id": 2, "name": "Acme"},
            "conversation": {
                "id": 123,
                "status": "open",
                "messages": [
                    {
                        "content": "Hola, necesito ayuda",
                        "account_id": 2,
                        "conversation_id": 123,
                        "source_id": "wamid.abc123",
                        "content_type": "text",
                        "content_attributes": {"media_url": None},
                        "created_at": "2024-01-15T10:00:00Z",
                        "sender_type": "Contact",
                        "sender": {
                            "identifier": "whatsapp:+58412XXXXXXX",
                            "phone_number": "+58412XXXXXXX",
                            "name": "Cliente Test",
                            "custom_attributes": {"estado": "ON"},
                        },
                        "attachments": [],
                    }
                ],
                "contact_inbox": {"contact_id": 456},
            },
            "sender": {"id": 789, "name": "Cliente Test", "phone_number": "+58412XXXXXXX"},
            "content": "Hola, necesito ayuda",
            "content_type": "text",
            "private": False,
        },
    }


# === Tests de validate_event ===


def test_validate_event_message_created(valid_webhook_payload):
    """Debe continuar si el evento es message_created."""
    state = create_initial_state(valid_webhook_payload)
    result = validate_event(state)

    assert result["event_type"] == "message_created"
    assert result["should_continue"] is True


def test_validate_event_other_event():
    """Debe detenerse si el evento no es message_created."""
    payload = {"body": {"event": "conversation_status_changed"}}
    state = create_initial_state(payload)
    result = validate_event(state)

    assert result["event_type"] == "conversation_status_changed"
    assert result["should_continue"] is False


def test_route_after_event_validation_continue():
    """Routing debe retornar 'continue' si should_continue es True."""
    state = {"should_continue": True}
    assert route_after_event_validation(state) == "continue"


def test_route_after_event_validation_stop():
    """Routing debe retornar 'stop' si should_continue es False."""
    state = {"should_continue": False}
    assert route_after_event_validation(state) == "stop"


# === Tests de validate_sender ===


def test_validate_sender_contact(valid_webhook_payload):
    """Debe continuar si el sender es Contact."""
    state = create_initial_state(valid_webhook_payload)
    result = validate_sender(state)

    assert result["sender_type"] == "Contact"
    assert result["should_continue"] is True


def test_validate_sender_agent(agent_message_payload):
    """Debe detenerse si el sender es User (agente)."""
    state = create_initial_state(agent_message_payload)
    result = validate_sender(state)

    assert result["sender_type"] == "User"
    assert result["should_continue"] is False


# === Tests de check_bot_state ===


def test_check_bot_state_on(valid_webhook_payload):
    """Debe continuar si el bot está ON."""
    state = create_initial_state(valid_webhook_payload)
    result = check_bot_state(state)

    assert result["bot_state"] == "ON"
    assert result["should_continue"] is True


def test_check_bot_state_off(bot_off_payload):
    """Debe detenerse si el bot está OFF."""
    state = create_initial_state(bot_off_payload)
    result = check_bot_state(state)

    assert result["bot_state"] == "OFF"
    assert result["should_continue"] is False


# === Tests de extract_message_data ===


def test_extract_message_data(valid_webhook_payload):
    """Debe extraer todos los datos del mensaje."""
    state = create_initial_state(valid_webhook_payload)
    result = extract_message_data(state)

    assert result["identifier"] == "whatsapp:+58412XXXXXXX"
    assert result["phone_number"] == "+58412XXXXXXX"
    assert result["user_name"] == "Cliente Test"
    assert result["account_id"] == 2
    assert result["conversation_id"] == 123
    assert result["contact_id"] == 456
    assert result["current_message"]["content"] == "Hola, necesito ayuda"
    assert result["current_message"]["source_id"] == "wamid.abc123"


def test_check_bot_state_gating_stop():
    payload = {
        "body": {
            "event": "message_created",
            "gating": {"stop": True},
            "conversation": {
                "messages": [
                    {
                        "content": "Hola",
                        "sender_type": "Contact",
                        "sender": {"custom_attributes": {"estado": "ON"}},
                    }
                ]
            },
        }
    }
    state = create_initial_state(payload)
    result = check_bot_state(state)
    assert result["bot_state"] == "ON"
    assert result["should_continue"] is False


def test_check_bot_state_ia_state_off_forces_stop():
    payload = {
        "body": {
            "event": "message_created",
            "ia_state": "off",
            "conversation": {
                "messages": [
                    {
                        "content": "Hola",
                        "account_id": 2,
                        "conversation_id": 123,
                        "source_id": "wamid.iaoff",
                        "sender_type": "Contact",
                        "sender": {
                            "identifier": "whatsapp:+58412ZZZZZZZ",
                            "phone_number": "+58412ZZZZZZZ",
                            "name": "Cliente IA Off",
                            "custom_attributes": {"estado": "ON"},
                        },
                    }
                ]
            },
        }
    }
    state = create_initial_state(payload)
    result = check_bot_state(state)
    assert result["bot_state"] == "OFF"
    assert result["should_continue"] is False
    assert result.get("conversation_id") == 123
    assert result.get("current_message", {}).get("source_id") == "wamid.iaoff"


def test_route_after_bot_check_stop_on_gating():
    payload = {
        "body": {
            "event": "message_created",
            "gating": {"stop_processing": True},
            "conversation": {
                "messages": [
                    {
                        "content": "Hola",
                        "sender_type": "Contact",
                        "sender": {"custom_attributes": {"estado": "ON"}},
                    }
                ]
            },
        }
    }
    state = create_initial_state(payload)
    result = check_bot_state(state)
    assert route_after_bot_check(result) == "stop"


def test_route_after_bot_check_escalate_when_forced():
    payload = {
        "body": {
            "event": "message_created",
            "gating": {"force_escalation": True},
            "conversation": {
                "messages": [
                    {
                        "content": "Hola",
                        "sender_type": "Contact",
                        "sender": {"custom_attributes": {"estado": "OFF"}},
                    }
                ]
            },
        }
    }
    state = create_initial_state(payload)
    result = check_bot_state(state)
    assert route_after_bot_check(result) == "escalate"


def test_extract_message_data_gating_flags():
    payload = {
        "body": {
            "event": "message_created",
            "gating": {"stop_processing": True, "force_escalation": True},
            "conversation": {
                "messages": [
                    {
                        "content": "Hola",
                        "account_id": 2,
                        "conversation_id": 123,
                        "source_id": "wamid.abc456",
                        "content_type": "text",
                        "created_at": "2024-01-15T10:00:00Z",
                        "sender_type": "Contact",
                        "sender": {
                            "identifier": "whatsapp:+58412YYYYYYY",
                            "phone_number": "+58412YYYYYYY",
                            "name": "Cliente Gating",
                            "custom_attributes": {"estado": "ON"},
                        },
                        "attachments": [],
                    }
                ],
                "contact_inbox": {"contact_id": 789},
            },
        }
    }
    state = create_initial_state(payload)
    result = extract_message_data(state)
    assert result["gating_stop"] is True
    assert result["gating_escalate"] is True


def test_flowify_wrapper_normalize_and_extract_fields(flowify_wrapper_payload_minimal):
    normalized = _normalize_inbound_payload(flowify_wrapper_payload_minimal)
    state = create_initial_state(normalized)
    state = validate_event(state)
    state = validate_sender(state)
    state = check_bot_state(state)
    result = extract_message_data(state)

    assert result["should_continue"] is True
    assert result["tenant_id"] == "10"
    assert result["tenant_slug"] == "acme"
    assert result["identifier"] == "whatsapp:+58412XXXXXXX"
    assert result["conversation_id"] == 123
    assert result["contact_id"] == 456
    assert result["gating_stop"] is False
    assert result["gating_escalate"] is True
    assert result["crm_memory"] == [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola!"},
    ]


def test_extract_message_data_fallback_tenant_data_when_no_messages():
    payload = {
        "body": {
            "event": "message_created",
            "vertical_id": "restaurante",
            "empresa_config": {
                "nombre": "Restaurante Neural",
                "horarios": "12:00 - 22:00",
                "oferta": "Pizza Trufada, Pasta al Pesto",
            },
            "conversation": {
                "messages": [],
            },
        }
    }
    state = create_initial_state(payload)
    result = extract_message_data(state)
    assert result["tenant_data"].get("nombre") == "Restaurante Neural"
    assert result["vertical_id"] == "restaurante"
