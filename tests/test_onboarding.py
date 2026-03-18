from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_normalize_preview_basic():
    sample = {
        "msg": {"text": "Hola", "id": "abc123"},
        "user": {"name": "Juan"},
    }
    mapping = {
        "body.conversation.messages[0].content": "msg.text",
        "body.conversation.messages[0].source_id": "msg.id",
        "body.conversation.messages[0].sender.name": "user.name",
    }
    resp = client.post(
        "/onboarding/normalize-preview",
        json={"source_name": "custom", "sample_payload": sample, "mapping": mapping},
    )
    assert resp.status_code == 200
    data = resp.json()
    preview = data["preview"]
    assert preview["body"]["conversation"]["messages"][0]["content"] == "Hola"
    assert preview["body"]["conversation"]["messages"][0]["sender"]["name"] == "Juan"
    assert preview["body"]["event"] == "message_created"


def test_save_and_get_mapping_in_memory_fallback():
    mapping = {"body.conversation.messages[0].content": "msg.text"}
    resp_save = client.post(
        "/onboarding/mapping",
        json={"source_name": "crm1", "mapping": mapping},
    )
    assert resp_save.status_code == 200
    resp_get = client.get("/onboarding/mapping/crm1")
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert data["source_name"] == "crm1"
    assert data["mapping"] == mapping


def test_generate_mapping_endpoint_with_fallback():
    sample = {
        "msg": {"text": "Hola", "id": "abc123"},
        "user": {"name": "Juan"},
    }
    resp = client.post(
        "/onboarding/generate-mapping",
        json={"source_name": "custom", "sample_payload": sample},
    )
    assert resp.status_code == 200
    data = resp.json()
    mapping = data["suggested"]
    assert isinstance(mapping, dict)
    assert data["preview"]["body"]["conversation"]["messages"][0]["content"] == "Hola"
    assert data["preview"]["body"]["conversation"]["messages"][0]["sender"]["name"] == "Juan"
    assert data["preview"]["body"]["event"] == "message_created"
    assert mapping.get("body.conversation.messages[0].content") == "msg.text"
    assert mapping.get("body.conversation.messages[0].sender.name") == "user.name"
    assert isinstance(data.get("used_ai"), bool)
