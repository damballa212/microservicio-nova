"""
Persistent memory storage in PostgreSQL.

Provides permanent storage for conversation history with:
- Unlimited retention by default
- Metadata tracking (tokens, model, timestamps)
- Advanced search capabilities
- Efficient indexing for fast queries
"""

import json
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PersistentMemory:
    """
    PostgreSQL-based permanent memory storage.

    Stores conversation history indefinitely with full metadata.
    Designed to work alongside Redis cache for optimal performance.
    """

    def __init__(self, postgres_url: str | None = None):
        """
        Initialize persistent memory connection.

        Args:
            postgres_url: PostgreSQL connection URL (defaults to settings)
        """
        self.postgres_url = postgres_url or settings.postgres_url
        self._conn = None

    def _get_connection(self):
        """Get or create PostgreSQL connection."""
        if self._conn is None or self._conn.closed:
            try:
                self._conn = psycopg2.connect(self.postgres_url)
                self._conn.autocommit = False  # Use transactions
            except Exception as e:
                logger.error("Failed to connect to PostgreSQL", error=str(e))
                raise
        return self._conn

    async def save_message(
        self,
        identifier: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Save a message to permanent storage.

        Args:
            identifier: User/conversation identifier
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Optional metadata (tokens, model, etc.)

        Returns:
            True if saved successfully
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            metadata_json = json.dumps(metadata or {})

            cursor.execute(
                """
                INSERT INTO chatbot.conversation_history
                    (identifier, role, content, metadata)
                VALUES (%s, %s, %s, %s)
                """,
                (identifier, role, content, metadata_json)
            )


            conn.commit()
            cursor.close()

            logger.debug(
                "Message saved to persistent storage",
                identifier=identifier,
                role=role,
                content_length=len(content),
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to save message to persistent storage",
                error=str(e),
                identifier=identifier,
            )
            if conn:
                conn.rollback()
            return False

    async def load_history(
        self,
        identifier: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Load conversation history from persistent storage.

        Args:
            identifier: User/conversation identifier
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of messages with metadata
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT id, identifier, role, content, metadata, created_at
                FROM chatbot.conversation_history
                WHERE identifier = %s
                ORDER BY created_at ASC
            """

            params: list[Any] = [identifier]

            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)

            if offset > 0:
                query += " OFFSET %s"
                params.append(offset)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()

            messages = []
            for row in rows:
                messages.append({
                    "id": row["id"],
                    "identifier": row["identifier"],
                    "role": row["role"],
                    "content": row["content"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                })

            logger.debug(
                "Loaded history from persistent storage",
                identifier=identifier,
                message_count=len(messages),
            )

            return messages

        except Exception as e:
            logger.error(
                "Failed to load history from persistent storage",
                error=str(e),
                identifier=identifier,
            )
            return []

    async def search_history(
        self,
        identifier: str | None = None,
        search_term: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Search conversation history with filters.

        Args:
            identifier: Optional user filter
            search_term: Optional text search in content
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum results

        Returns:
            List of matching messages
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            conditions = []
            params: list[Any] = []

            if identifier:
                conditions.append("identifier = %s")
                params.append(identifier)

            if search_term:
                conditions.append("content ILIKE %s")
                params.append(f"%{search_term}%")

            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            query = f"""
                SELECT id, identifier, role, content, metadata, created_at
                FROM chatbot.conversation_history
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """

            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()

            messages = []
            for row in rows:
                messages.append({
                    "id": row["id"],
                    "identifier": row["identifier"],
                    "role": row["role"],
                    "content": row["content"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                })

            return messages

        except Exception as e:
            logger.error("Failed to search history", error=str(e))
            return []

    async def get_stats(self, identifier: str) -> dict[str, Any]:
        """
        Get conversation statistics for a user.

        Args:
            identifier: User/conversation identifier

        Returns:
            Dictionary with stats (total messages, date range, etc.)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_messages,
                    MIN(created_at) as first_message,
                    MAX(created_at) as last_message,
                    SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages
                FROM chatbot.conversation_history
                WHERE identifier = %s
                """,
                (identifier,)
            )

            row = cursor.fetchone()
            cursor.close()

            return {
                "total_messages": row["total_messages"] or 0,
                "user_messages": row["user_messages"] or 0,
                "assistant_messages": row["assistant_messages"] or 0,
                "first_message": row["first_message"].isoformat() if row["first_message"] else None,
                "last_message": row["last_message"].isoformat() if row["last_message"] else None,
            }

        except Exception as e:
            logger.error("Failed to get stats", error=str(e))
            return {}

    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.debug("Closed PostgreSQL connection")


# Global instance
persistent_memory = PersistentMemory()
