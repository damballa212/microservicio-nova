import json
from datetime import datetime, timedelta

import pytest

from src.config.settings import settings
from src.memory import semantic_memory
from src.memory.persistent_memory import persistent_memory
from src.utils.redis_client import redis_client


@pytest.mark.asyncio
async def test_maybe_enqueue_episode_threshold(monkeypatch):
    monkeypatch.setattr(settings, "semantic_episode_trigger_every_messages", 3)

    async def fake_get_stats(identifier: str):
        return {
            "total_messages": 3,
            "last_message": datetime.now().isoformat(),
        }

    async def fake_group_create(stream: str, group: str):
        return None

    calls: list[dict] = []

    async def fake_stream_add(stream: str, fields: dict[str, str], maxlen: int | None = None):
        calls.append({"stream": stream, "fields": dict(fields)})
        return "0-1"

    monkeypatch.setattr(persistent_memory, "get_stats", fake_get_stats)
    monkeypatch.setattr(redis_client, "stream_group_create", fake_group_create)
    monkeypatch.setattr(redis_client, "stream_add", fake_stream_add)

    ok = await semantic_memory.maybe_enqueue_episode("1", "user-1")
    assert ok is True
    assert len(calls) == 1
    payload = json.loads(calls[0]["fields"]["payload"])
    assert payload["identifier"] == "user-1"


@pytest.mark.asyncio
async def test_maybe_enqueue_episode_inactivity(monkeypatch):
    monkeypatch.setattr(settings, "semantic_episode_trigger_every_messages", 999)
    monkeypatch.setattr(settings, "semantic_episode_inactivity_minutes", 1)

    past = datetime.now() - timedelta(minutes=2)

    async def fake_get_stats(identifier: str):
        return {
            "total_messages": 1,
            "last_message": past.isoformat(),
        }

    async def fake_group_create(stream: str, group: str):
        return None

    calls: list[dict] = []

    async def fake_stream_add(stream: str, fields: dict[str, str], maxlen: int | None = None):
        calls.append({"stream": stream, "fields": dict(fields)})
        return "0-2"

    monkeypatch.setattr(persistent_memory, "get_stats", fake_get_stats)
    monkeypatch.setattr(redis_client, "stream_group_create", fake_group_create)
    monkeypatch.setattr(redis_client, "stream_add", fake_stream_add)

    ok = await semantic_memory.maybe_enqueue_episode("2", "user-2")
    assert ok is True
    assert len(calls) == 1
    payload = json.loads(calls[0]["fields"]["payload"])
    assert payload["empresa_id"] == "2"


@pytest.mark.asyncio
async def test_enqueue_episode_job_builds_payload(monkeypatch):
    calls: list[dict] = []

    async def fake_group_create(stream: str, group: str):
        return None

    async def fake_stream_add(stream: str, fields: dict[str, str], maxlen: int | None = None):
        calls.append({"stream": stream, "fields": dict(fields)})
        return "0-3"

    monkeypatch.setattr(redis_client, "stream_group_create", fake_group_create)
    monkeypatch.setattr(redis_client, "stream_add", fake_stream_add)

    ok = await semantic_memory.enqueue_episode_job("3", "user-3", window_size=10, episode_id="ep-1")
    assert ok is True
    assert len(calls) == 1
    payload = json.loads(calls[0]["fields"]["payload"])
    assert payload["empresa_id"] == "3"
    assert payload["identifier"] == "user-3"
    assert payload["window_size"] == 10
    assert payload["episode_id"] == "ep-1"
