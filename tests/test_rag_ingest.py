import io

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_rag_ingest_upload_pdf_small():
    data = io.BytesIO(b"%PDF-1.4\n%test")
    files = {
        "file": ("test.pdf", data, "application/pdf"),
    }
    form = {
        "empresa_id": "1",
        "empresa_slug": "tenant-a",
        "doc_id": "doc-123",
    }
    r = client.post("/rag/ingest/upload", files=files, data=form)
    assert r.status_code == 200
    js = r.json()
    assert js.get("status") == "received"
    assert js.get("doc_id") == "doc-123"


def test_rag_ingest_notify_minimal():
    body = {
        "empresa_id": 1,
        "empresa_slug": "tenant-a",
        "doc_id": "doc-xyz",
        "presigned_url": "https://example.com/file.pdf?sig=abc",
        "mime": "application/pdf",
        "size": 10,
        "hash_sha256": "abc",
    }
    r = client.post("/rag/ingest/notify", json=body)
    assert r.status_code == 200
    js = r.json()
    assert js.get("status") == "received"
    assert js.get("doc_id") == "doc-xyz"
