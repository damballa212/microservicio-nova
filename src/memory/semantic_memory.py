"""
Semantic Conversational Memory (Episodes) using PostgreSQL + pgvector.

Provides episodic summaries of conversations for semantic retrieval beyond the
recent window kept in Redis. Keeps strong multi-tenant isolation via empresa_id
and identifier namespacing.
"""

from datetime import datetime
from typing import Any

from src.config.settings import settings
from src.memory.persistent_memory import persistent_memory
from src.rag.embeddings import get_embedding_fn
from src.utils.logger import get_logger
from src.utils.redis_client import redis_client

logger = get_logger(__name__)


def _get_pg_conn():
    import os

    url = os.getenv("POSTGRES_URL") or settings.postgres_url
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        import psycopg2

        return psycopg2.connect(url)
    except Exception:
        return None


def _ensure_episode_schema(conn) -> None:
    try:
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {settings.pg_schema}.{settings.pg_semantic_memory_table} (
              id BIGSERIAL PRIMARY KEY,
              empresa_id TEXT,
              identifier TEXT,
              episode_id TEXT,
              summary TEXT,
              embedding VECTOR(1536),
              episode_started_at TIMESTAMP,
              episode_ended_at TIMESTAMP,
              created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{settings.pg_semantic_memory_table}_unique ON {settings.pg_schema}.{settings.pg_semantic_memory_table}(empresa_id, identifier, episode_id)"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{settings.pg_semantic_memory_table}_empid ON {settings.pg_schema}.{settings.pg_semantic_memory_table}(empresa_id, identifier)"
        )
        conn.commit()
        cur.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def upsert_episode(
    empresa_id: str,
    identifier: str,
    episode_id: str,
    summary_text: str,
    episode_started_at: datetime | None = None,
    episode_ended_at: datetime | None = None,
) -> bool:
    conn = _get_pg_conn()
    if conn is None:
        return False
    _ensure_episode_schema(conn)
    try:
        import pgvector

        pgvector.register_vector(conn)
    except Exception:
        pass

    try:
        emb = get_embedding_fn()
        vec = emb.embed_query(summary_text or "")
        if not vec:
            logger.warning("Empty embedding vector, skipping episode upsert")
            return False
        cur = conn.cursor()
        cur.execute(
            f"""
            INSERT INTO {settings.pg_schema}.{settings.pg_semantic_memory_table}
              (empresa_id, identifier, episode_id, summary, embedding, episode_started_at, episode_ended_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (empresa_id, identifier, episode_id)
            DO UPDATE SET summary = EXCLUDED.summary, embedding = EXCLUDED.embedding, episode_started_at = EXCLUDED.episode_started_at, episode_ended_at = EXCLUDED.episode_ended_at
            """,
            (
                str(empresa_id),
                str(identifier),
                str(episode_id),
                str(summary_text or ""),
                vec,
                episode_started_at,
                episode_ended_at,
            ),
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error("Failed to upsert episode", error=str(e))
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


def search_episodes(
    empresa_id: str,
    identifier: str,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
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
        qv = emb.embed_query(query or "")
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT episode_id, summary, episode_started_at, episode_ended_at
            FROM {settings.pg_schema}.{settings.pg_semantic_memory_table}
            WHERE empresa_id = %s AND identifier = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (str(empresa_id), str(identifier), qv, int(top_k)),
        )
        rows = cur.fetchall()
        cur.close()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "episode_id": str(r[0] or ""),
                    "summary": str(r[1] or ""),
                    "started_at": r[2].isoformat() if r[2] else None,
                    "ended_at": r[3].isoformat() if r[3] else None,
                }
            )
        return out
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


async def enqueue_episode_job(
    empresa_id: str,
    identifier: str,
    window_size: int | None = None,
    episode_id: str | None = None,
) -> bool:
    """
    Encola un trabajo de consolidación de episodio semántico.

    Args:
        empresa_id: ID del tenant
        identifier: Identificador de usuario/conversación
        window_size: Número de mensajes a consolidar (default: settings)
        episode_id: ID del episodio (opcional)

    Returns:
        True si fue encolado exitosamente
    """
    try:
        ws = int(window_size or settings.semantic_episode_window_size or 15)
        payload = {
            "empresa_id": str(empresa_id),
            "identifier": str(identifier),
            "window_size": ws,
            "episode_id": episode_id or "",
        }
        await redis_client.stream_group_create(
            settings.semantic_episode_stream_key, settings.semantic_episode_stream_group
        )
    except Exception:
        pass
    try:
        await redis_client.stream_add(
            settings.semantic_episode_stream_key,
            {"payload": __import__("json").dumps(payload, ensure_ascii=False)},
            maxlen=5000,
        )
        return True
    except Exception:
        return False


async def maybe_enqueue_episode(empresa_id: str, identifier: str) -> bool:
    """
    Verifica umbral y encola episodio si corresponde.

    Usa total de mensajes persistentes como contador global.
    """
    try:
        stats = await persistent_memory.get_stats(identifier)
        total = int(stats.get("total_messages") or 0)
        threshold = int(settings.semantic_episode_trigger_every_messages or 12)
        if total > 0 and threshold > 0 and (total % threshold == 0):
            return await enqueue_episode_job(empresa_id, identifier)
        lm = stats.get("last_message")
        if isinstance(lm, str) and lm:
            try:
                import datetime as _dt
                t = _dt.datetime.fromisoformat(lm.replace("Z", "+00:00"))
                diff = _dt.datetime.now(_dt.UTC) - t.astimezone(_dt.UTC)
                mins = diff.total_seconds() / 60.0
                if mins >= int(settings.semantic_episode_inactivity_minutes or 0):
                    return await enqueue_episode_job(empresa_id, identifier)
            except Exception:
                pass
        return False
    except Exception:
        return False
