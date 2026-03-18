"""
Tests para la API.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.router import _normalize_inbound_payload
from src.config.settings import settings
from src.main import app
from src.models.state import create_initial_state
from src.nodes.outbound_webhook import post_to_outbound_webhook
from src.nodes.validation import extract_message_data

client = TestClient(app)


def test_health_check():
    """Health check debe retornar status healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "chatbot-whatsapp"


def test_root():
    """Endpoint raíz debe retornar info del servicio."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data


def test_graph_diagram():
    """Debe retornar el diagrama Mermaid del grafo."""
    response = client.get("/graph/diagram")
    assert response.status_code == 200
    # Debe contener sintaxis Mermaid
    assert (
        "graph" in response.text.lower()
        or "flowchart" in response.text.lower()
        or "statediagram" in response.text.lower()
        or "#" in response.text
    )


def test_webhook_invalid_payload():
    """Webhook con payload inválido debe retornar error."""
    response = client.post(
        "/webhook/inbound",
        json={},  # Payload vacío
    )
    # Aún debe aceptar el webhook (procesamiento en background)
    assert response.status_code == 200


def test_webhook_legacy_chatwoot_route():
    response = client.post(
        "/webhook/chatwoot",
        json={},
    )
    assert response.status_code == 200


def test_normalize_flowify_wrapper_chatwoot_payload():
    payload = {
        "empresa_id": 1,
        "empresa_slug": "pizzeria-lalo",
        "ia_state": "off",
        "schema_version": "1.0",
        "trace_id": "trace_123",
        "idempotency_key": "chatwoot:account:21:conv:2:msg:5172",
        "timestamp_received": "2025-12-13T01:31:47.120Z",
        "gating": {"stop_processing": False, "force_escalation": True},
        "memoria_conversacional": [
            {"role": "user", "content": "hola", "timestamp": "2025-12-13T01:30:00Z"},
            {"role": "assistant", "content": "hola!", "timestamp": "2025-12-13T01:30:05Z"},
        ],
        "chatwoot_payload": {
            "event": "message_created",
            "message_type": "incoming",
            "conversation": {
                "messages": [
                    {
                        "content": "Tienen pizzas?",
                        "account_id": 21,
                        "conversation_id": 2,
                        "source_id": 5172,
                        "content_type": "text",
                        "content_attributes": {"media_url": None},
                        "created_at": "2025-12-13T01:31:46.790Z",
                        "sender_type": "Contact",
                        "sender": {
                            "identifier": "whatsapp:+584122236071",
                            "phone_number": "+584122236071",
                            "name": "Marlon Pernia",
                            "custom_attributes": {"estado": "ON"},
                        },
                        "attachments": [],
                    }
                ],
                "contact_inbox": {"contact_id": 456},
            },
            "private": False,
        },
    }

    normalized = _normalize_inbound_payload(payload)
    body = normalized["body"]
    assert body["event"] == "message_created"
    assert body["empresa_id"] == 1
    assert body["empresa_slug"] == "pizzeria-lalo"
    assert body["ia_state"] == "off"
    assert body["schema_version"] == "1.0"
    assert body["trace_id"] == "trace_123"
    assert body["idempotency_key"] == "chatwoot:account:21:conv:2:msg:5172"
    assert body["timestamp_received"] == "2025-12-13T01:31:47.120Z"
    assert body["gating"]["force_escalation"] is True
    assert body["conversation"]["messages"][0]["sender_type"] == "Contact"


@pytest.mark.asyncio
async def test_outbound_payload_contract_fields(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_send(payload: dict[str, object]):
        captured.update(payload)
        return {"status_code": 200, "data": {"ok": True}}

    monkeypatch.setattr(settings, "outbound_webhook_base_url", "http://example.com")
    monkeypatch.setattr("src.nodes.outbound_webhook.outbound_webhook_client.send", fake_send)

    payload_in = {
        "body": {
            "event": "message_created",
            "empresa_id": 1,
            "empresa_slug": "pizzeria-lalo",
            "trace_id": "trace_abc",
            "idempotency_key": "idem_abc",
            "timestamp_received": "2025-12-13T01:31:47.120Z",
            "conversation": {
                "messages": [
                    {
                        "content": "Hola",
                        "account_id": 21,
                        "conversation_id": 2,
                        "source_id": 5172,
                        "content_type": "text",
                        "created_at": "2025-12-13T01:31:46.790Z",
                        "sender_type": "Contact",
                        "sender": {
                            "identifier": "whatsapp:+584122236071",
                            "phone_number": "+584122236071",
                            "name": "Marlon Pernia",
                            "custom_attributes": {"estado": "ON"},
                        },
                        "attachments": [],
                    }
                ],
                "contact_inbox": {"contact_id": 456},
            },
        }
    }

    state = create_initial_state(payload_in)
    state = extract_message_data(state)
    state["ai_response"] = "Hola!"
    state["formatted_parts"] = ["Hola!"]
    state["needs_escalation"] = True
    state["escalation_reason"] = "Escalar"
    state["actions"] = {"apply_labels": ["asistencia_ia"], "intent": "consulta"}

    await post_to_outbound_webhook(state)

    assert captured.get("trace_id") == "trace_abc"
    assert captured.get("idempotency_key") == "idem_abc"
    assert captured.get("timestamp_received") == "2025-12-13T01:31:47.120Z"

    respuesta = captured.get("respuesta_agente")
    assert isinstance(respuesta, dict)
    assert respuesta.get("texto") == "Hola!"
    assert respuesta.get("partes") == ["Hola!"]

    assert captured.get("intencion_detectada") == "consulta"
    assert captured.get("etiquetas_aplicadas") == ["asistencia_ia"]
    assert captured.get("escalate_to_human") is True


def test_normalize_raw_chatwoot_shape_to_messages_list():
    payload = {
        "event": "message_created",
        "account": {"id": 21},
        "conversation": {"id": 2, "custom_attributes": {"bot_status": "ON"}},
        "content": "Hola",
        "content_type": "text",
        "source_id": "wamid.1",
        "sender": {
            "type": "contact",
            "identifier": "whatsapp:+58412",
            "phone_number": "+58412",
            "name": "Cliente",
            "custom_attributes": {"estado": "ON"},
        },
    }
    normalized = _normalize_inbound_payload(payload)
    msg = normalized["body"]["conversation"]["messages"][0]
    assert msg["content"] == "Hola"
    assert msg["sender_type"] == "Contact"
    assert msg["conversation_id"] == 2
    assert msg["account_id"] == 21
