import pytest

from src.models.state import create_initial_state
from src.nodes.escalation import classify_escalation, escalate_to_human, route_escalation


@pytest.mark.asyncio
async def test_classify_escalation_forced():
    payload = {
        "body": {
            "event": "message_created",
            "conversation": {
                "messages": [{"content": "Hola", "sender_type": "Contact", "sender": {}}]
            },
        }
    }
    state = create_initial_state(payload)
    state["gating_escalate"] = True
    state["chat_input"] = "Necesito ayuda urgente"
    result = await classify_escalation(state)
    assert result["needs_escalation"] is True
    assert result["escalation_reason"] == "Escalamiento forzado por CRM"
    m = result.get("_node_metrics") or {}
    assert m.get("provider") is None
    assert m.get("input_tokens") == 0
    assert m.get("output_tokens") == 0
    assert m.get("total_tokens") == 0


def test_route_escalation_escalate_when_true():
    state = {"needs_escalation": True}
    assert route_escalation(state) == "escalate"


def test_route_escalation_continue_when_false():
    state = {"needs_escalation": False}
    assert route_escalation(state) == "continue"


@pytest.mark.asyncio
async def test_escalate_to_human_sets_actions():
    state = create_initial_state({"body": {"event": "message_created"}})
    state["conversation_id"] = 100
    state["contact_id"] = 200
    state["phone_number"] = "+11111111111"
    result = await escalate_to_human(state)

    assert result.get("error") is None
    assert result.get("needs_escalation") is True
    assert result.get("escalation_reason") is not None

    actions = result.get("actions")
    assert isinstance(actions, dict)
    assert actions.get("set_ia_state") == "OFF"
    assert isinstance(actions.get("send_message"), str)

    labels = actions.get("apply_labels")
    assert isinstance(labels, list)
    assert "asistencia_ia" in labels
    assert "escalado" in labels
