import os

from src.config.settings import settings
from src.rag.embeddings import get_embedding_fn


def _get_pg_conn():
    url = os.getenv("POSTGRES_URL") or settings.postgres_url
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        import psycopg2

        return psycopg2.connect(url)
    except Exception:
        return None


def _ensure_schema(conn) -> None:
    try:
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {settings.pg_schema}.{settings.pgvector_table} (
              id BIGSERIAL PRIMARY KEY,
              empresa_id TEXT,
              doc_id TEXT,
              title TEXT,
              content TEXT,
              mime TEXT,
              tags TEXT,
              embedding VECTOR(1536),
              created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{settings.pgvector_table}_doc ON {settings.pg_schema}.{settings.pgvector_table}(doc_id)"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{settings.pgvector_table}_emp ON {settings.pg_schema}.{settings.pgvector_table}(empresa_id)"
        )
        conn.commit()
        cur.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _delete_doc(conn, empresa_id: str, doc_id: str) -> None:
    try:
        cur = conn.cursor()
        cur.execute(
            f"DELETE FROM {settings.pg_schema}.{settings.pgvector_table} WHERE empresa_id = %s AND doc_id = %s",
            (str(empresa_id), str(doc_id)),
        )
        conn.commit()
        cur.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def upsert_chunks(
    empresa_id: str,
    doc_id: str,
    title: str | None,
    mime: str | None,
    tags: str | None,
    chunks: list[str],
) -> bool:
    conn = _get_pg_conn()
    if conn is None:
        return False
    _ensure_schema(conn)
    try:
        import pgvector

        pgvector.register_vector(conn)
    except Exception:
        pass
    try:
        _delete_doc(conn, str(empresa_id), str(doc_id))
        emb = get_embedding_fn()
        vecs = emb.embed_documents(chunks)
        cur = conn.cursor()
        for i, chunk in enumerate(chunks):
            v = vecs[i] if i < len(vecs) else None
            cur.execute(
                f"""
                INSERT INTO {settings.pg_schema}.{settings.pgvector_table}
                  (empresa_id, doc_id, title, content, mime, tags, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(empresa_id),
                    str(doc_id),
                    str(title or ""),
                    str(chunk or ""),
                    str(mime or ""),
                    str(tags or ""),
                    v,
                ),
            )
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def similarity_search(
    empresa_id: str,
    query: str,
    top_k: int,
) -> list[tuple[str, str]]:
    conn = _get_pg_conn()
    if conn is None:
        return []
    try:
        import pgvector

        pgvector.register_vector(conn)
    except Exception:
        pass
    try:
        emb = get_embedding_fn()
        qv = emb.embed_query(query)
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT title, content FROM {settings.pg_schema}.{settings.pgvector_table}
            WHERE empresa_id = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (str(empresa_id), qv, int(top_k)),
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for r in rows:
            t = r[0] or ""
            c = r[1] or ""
            out.append((t, c))
        return out
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def upsert_metadata(
    empresa_id: str,
    doc_id: str,
    title: str | None,
    url: str | None,
    schema: str | None,
) -> bool:
    conn = _get_pg_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {settings.pg_schema}.{settings.pg_document_metadata_table} (
              id TEXT PRIMARY KEY,
              title TEXT,
              url TEXT,
              schema TEXT,
              created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"INSERT INTO {settings.pg_schema}.{settings.pg_document_metadata_table} (id, title, url, schema) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, url=EXCLUDED.url, schema=EXCLUDED.schema",
            (str(doc_id), str(title or ""), str(url or ""), str(schema or "")),
        )
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def insert_rows(empresa_id: str, doc_id: str, rows: list[dict]) -> bool:
    conn = _get_pg_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {settings.pg_schema}.{settings.pg_document_rows_table} (
              id BIGSERIAL PRIMARY KEY,
              dataset_id TEXT,
              row_data JSONB,
              created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"DELETE FROM {settings.pg_schema}.{settings.pg_document_rows_table} WHERE dataset_id = %s",
            (str(doc_id),),
        )
        for r in rows:
            cur.execute(
                f"INSERT INTO {settings.pg_schema}.{settings.pg_document_rows_table} (dataset_id, row_data) VALUES (%s, %s)",
                (str(doc_id), __import__("json").dumps(r, ensure_ascii=False)),
            )
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


async def reranked_search(
    empresa_id: str,
    query: str,
    top_k: int,
) -> list[dict]:
    base = similarity_search(empresa_id, query, top_k)
    docs = [{"title": t, "content": c} for (t, c) in base]
    if not docs:
        return []
    if not settings.rag_reranker_enabled:
        return docs
    if not isinstance(settings.cohere_api_key, str) or not settings.cohere_api_key.strip():
        return docs
    try:
        import httpx

        payload = {
            "query": query,
            "documents": [d.get("content") or "" for d in docs],
            "top_n": min(len(docs), max(1, top_k)),
            "return_documents": True,
            "model": "rerank-3",
        }
        headers = {
            "Authorization": f"Bearer {settings.cohere_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post("https://api.cohere.com/v1/rerank", json=payload, headers=headers)
        if resp.status_code >= 400:
            return docs
        data = resp.json()
        results = data.get("results") or []
        scored: list[tuple[float, int]] = []
        for r in results:
            idx = r.get("index")
            score = r.get("relevance_score")
            if isinstance(idx, int) and isinstance(score, (int, float)):
                scored.append((float(score), int(idx)))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[dict] = []
        for _, i in scored[: len(docs)]:
            if 0 <= i < len(docs):
                out.append(docs[i])
        return out if out else docs
    except Exception:
        return docs


# NUEVAS FUNCIONES PARA GESTIÓN DE DOCUMENTOS

def list_docs(empresa_id: str) -> list[dict]:
    conn = _get_pg_conn()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT DISTINCT ON (doc_id) doc_id, title, mime, tags, created_at
            FROM {settings.pg_schema}.{settings.pgvector_table}
            WHERE empresa_id = %s
            ORDER BY doc_id, created_at DESC
            """,
            (str(empresa_id),),
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for r in rows:
            out.append({
                "doc_id": r[0] or "",
                "title": r[1] or "",
                "mime": r[2] or "",
                "tags": r[3] or "",
                "created_at": r[4].isoformat() if r[4] else None,
            })
        return out
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def delete_doc_complete(empresa_id: str, doc_id: str) -> bool:
    """Elimina completamente un documento y sus chunks."""
    conn = _get_pg_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        # Borrar filas de vector store
        cur.execute(
            f"DELETE FROM {settings.pg_schema}.{settings.pgvector_table} WHERE empresa_id = %s AND doc_id = %s",
            (str(empresa_id), str(doc_id)),
        )
        # Borrar metadata (si existe por id)
        cur.execute(
            f"DELETE FROM {settings.pg_schema}.{settings.pg_document_metadata_table} WHERE id = %s",
            (str(doc_id),),
        )
        # Borrar filas raw (si existen)
        cur.execute(
             f"DELETE FROM {settings.pg_schema}.{settings.pg_document_rows_table} WHERE dataset_id = %s",
             (str(doc_id),)
        )
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass
