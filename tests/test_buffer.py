import json
from datetime import UTC, datetime, timedelta

import pytest

from src.buffer.buffer_manager import buffer_manager
from src.nodes.buffer import route_buffer_decision
from src.utils.redis_client import redis_client


@pytest.mark.asyncio
async def test_check_status_wait(monkeypatch):
    identifier = "whatsapp:+10000000000"

    now = datetime.now(UTC)
    older = (now - timedelta(seconds=20)).isoformat()
    recent = (now - timedelta(seconds=2)).isoformat()

    messages = [
        json.dumps(
            {
                "content": "Hola",
                "content_type": "text",
                "source_id": "old_msg",
                "created_at": older,
            }
        ),
        json.dumps(
            {
                "content": "Necesito ayuda",
                "content_type": "text",
                "source_id": "current_msg",
                "created_at": recent,
            }
        ),
    ]

    async def fake_get_list(key: str):
        return messages

    monkeypatch.setattr(redis_client, "get_list", fake_get_list)

    buffer_manager.wait_seconds = 10

    action = await buffer_manager.check_status(identifier, "current_msg")
    assert action == "wait"


@pytest.mark.asyncio
async def test_check_status_process(monkeypatch):
    identifier = "whatsapp:+10000000001"

    now = datetime.now(UTC)
    older = (now - timedelta(seconds=40)).isoformat()
    recent = (now - timedelta(seconds=15)).isoformat()

    messages = [
        json.dumps(
            {
                "content": "Hola",
                "content_type": "text",
                "source_id": "old_msg",
                "created_at": older,
            }
        ),
        json.dumps(
            {
                "content": "Necesito ayuda",
                "content_type": "text",
                "source_id": "current_msg",
                "created_at": recent,
            }
        ),
    ]

    async def fake_get_list(key: str):
        return messages

    monkeypatch.setattr(redis_client, "get_list", fake_get_list)

    buffer_manager.wait_seconds = 10

    action = await buffer_manager.check_status(identifier, "current_msg")
    assert action == "process"


@pytest.mark.asyncio
async def test_check_status_duplicate(monkeypatch):
    identifier = "whatsapp:+10000000002"

    now = datetime.now(UTC)
    recent = (now - timedelta(seconds=2)).isoformat()

    messages = [
        json.dumps(
            {
                "content": "Necesito ayuda",
                "content_type": "text",
                "source_id": "new_msg",
                "created_at": recent,
            }
        ),
    ]

    async def fake_get_list(key: str):
        return messages

    monkeypatch.setattr(redis_client, "get_list", fake_get_list)

    buffer_manager.wait_seconds = 10

    action = await buffer_manager.check_status(identifier, "old_msg")
    assert action == "duplicate"


@pytest.mark.asyncio
async def test_wait_and_check_eventual_process(monkeypatch):
    identifier = "whatsapp:+10000000003"

    now = datetime.now(UTC)
    recent = now.isoformat()

    messages = [
        json.dumps(
            {
                "content": "Hola",
                "content_type": "text",
                "source_id": "current_msg",
                "created_at": recent,
            }
        )
    ]

    async def fake_get_list(key: str):
        return messages

    monkeypatch.setattr(redis_client, "get_list", fake_get_list)

    buffer_manager.wait_seconds = 0.05

    action, out_messages = await buffer_manager.wait_and_check(
        identifier, "current_msg", max_iterations=2
    )
    assert action == "process"
    assert isinstance(out_messages, list)
    assert len(out_messages) == 1


@pytest.mark.asyncio
async def test_wait_and_check_skip(monkeypatch):
    identifier = "whatsapp:+10000000004"

    async def fake_get_list(key: str):
        return []

    monkeypatch.setattr(redis_client, "get_list", fake_get_list)

    buffer_manager.wait_seconds = 0.05

    action, out_messages = await buffer_manager.wait_and_check(
        identifier, "current_msg", max_iterations=1
    )
    assert action == "skip"
    assert out_messages == []


@pytest.mark.asyncio
async def test_wait_and_check_duplicate(monkeypatch):
    identifier = "whatsapp:+10000000005"

    now = datetime.now(UTC)
    recent = now.isoformat()

    messages = [
        json.dumps(
            {
                "content": "Necesito ayuda",
                "content_type": "text",
                "source_id": "new_msg",
                "created_at": recent,
            }
        )
    ]

    async def fake_get_list(key: str):
        return messages

    monkeypatch.setattr(redis_client, "get_list", fake_get_list)

    buffer_manager.wait_seconds = 0.05

    action, out_messages = await buffer_manager.wait_and_check(
        identifier, "old_msg", max_iterations=2
    )
    assert action == "duplicate"
    assert out_messages == []


def test_route_buffer_decision():
    state = {"buffer_action": "wait"}
    assert route_buffer_decision(state) == "wait"
    state = {"buffer_action": "process"}
    assert route_buffer_decision(state) == "process"
    state = {"buffer_action": "duplicate"}
    assert route_buffer_decision(state) == "duplicate"
    state = {"buffer_action": "skip"}
    assert route_buffer_decision(state) == "duplicate"
