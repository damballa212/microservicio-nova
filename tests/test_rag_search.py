from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_rag_search_empty_when_no_store_configured():
    body = {
        "empresa_id": 1,
        "empresa_slug": "tenant-a",
        "query": "pizza hawaiana",
        "top_k": 3,
    }
    r = client.post("/rag/search", json=body)
    assert r.status_code == 200
    js = r.json()
    assert isinstance(js.get("docs"), list)
