import pytest

from src.config.settings import settings
from src.models.state import create_initial_state
from src.nodes.nlu import classify_intent, classify_intent_llm, score_lead, score_lead_llm


@pytest.mark.asyncio
async def test_classify_intent_price_sets_intent_and_labels():
    state = create_initial_state({"body": {"event": "message_created"}})
    state["chat_input"] = "Cuánto cuesta la pizza grande?"

    result = await classify_intent(state)
    actions = result.get("actions")
    assert isinstance(actions, dict)
    assert actions.get("intencion_detectada") == "consulta_precio"
    labels = actions.get("apply_labels")
    assert isinstance(labels, list)
    assert "consulta_precio" in labels


@pytest.mark.asyncio
async def test_score_lead_true_for_price_intent_adds_label():
    state = create_initial_state({"body": {"event": "message_created"}})
    state["chat_input"] = "Cuánto cuesta?"
    state["actions"] = {
        "intencion_detectada": "consulta_precio",
        "apply_labels": ["consulta_precio"],
    }

    result = await score_lead(state)
    actions = result.get("actions")
    assert isinstance(actions, dict)
    assert actions.get("lead_calificado") is True
    labels = actions.get("apply_labels")
    assert isinstance(labels, list)
    assert "lead_calificado" in labels


@pytest.mark.asyncio
async def test_classify_intent_llm_falls_back_to_heuristic(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "google_api_key", "")

    state = create_initial_state({"body": {"event": "message_created"}})
    state["chat_input"] = "Tienen stock de pizza margarita?"
    result = await classify_intent_llm(state)
    actions = result.get("actions")
    assert isinstance(actions, dict)
    assert actions.get("intencion_detectada") == "consulta_disponibilidad"


@pytest.mark.asyncio
async def test_score_lead_llm_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "google_api_key", "")

    state = create_initial_state({"body": {"event": "message_created"}})
    state["chat_input"] = "Tienen stock?"
    state["actions"] = {
        "intencion_detectada": "consulta_disponibilidad",
        "apply_labels": ["consulta_disponibilidad"],
    }

    result = await score_lead_llm(state)
    actions = result.get("actions")
    assert isinstance(actions, dict)
    assert actions.get("lead_calificado") is True
