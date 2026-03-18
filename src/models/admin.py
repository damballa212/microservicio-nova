"""
Modelos y capa de acceso a datos para la administración del sistema.
"""

import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import psycopg2
from cryptography.fernet import Fernet
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


# === ENCRYPTION UTILITIES ===

def _get_fernet_key() -> bytes:
    """Get or generate Fernet encryption key."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        # Fallback: generate from a secret (not ideal for production)
        import hashlib
        secret = os.environ.get("N8N_WEBHOOK_SECRET", "default-secret-key")
        key = hashlib.sha256(secret.encode()).digest()[:32]
        import base64
        key = base64.urlsafe_b64encode(key).decode()
    return key.encode() if isinstance(key, str) else key


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt an API key using Fernet."""
    f = Fernet(_get_fernet_key())
    return f.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key using Fernet."""
    f = Fernet(_get_fernet_key())
    return f.decrypt(encrypted_key.encode()).decode()


def mask_api_key(key: str) -> str:
    """Show only last 4 characters of API key."""
    if len(key) <= 8:
        return "****"
    return f"{key[:6]}...{key[-4:]}"


# === ENUMS ===

class CredentialProvider(str, Enum):
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    MISTRAL = "mistral"
    OTHER = "other"


# === PYDANTIC MODELS ===

class SystemConfig(BaseModel):
    """Modelo para configuraciones del sistema."""
    key: str
    value: str
    description: Optional[str] = None
    is_secret: bool = False
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class SystemConfigUpdate(BaseModel):
    """Modelo para actualizar configuraciones."""
    value: str
    description: Optional[str] = None
    updated_by: Optional[str] = None


class PromptTemplate(BaseModel):
    """Modelo para plantillas de prompts."""
    id: Optional[int] = None
    name: str
    content: str
    version: int = 1
    is_active: bool = True
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class PromptTemplateCreate(BaseModel):
    """Modelo para crear/actualizar plantillas."""
    name: str
    content: str
    description: Optional[str] = None
    updated_by: Optional[str] = None


class AdminUser(BaseModel):
    """Modelo para usuario administrador."""
    id: Optional[int] = None
    email: str
    role: str = "admin"
    full_name: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None


class ApiCredential(BaseModel):
    """Modelo para credenciales de API."""
    id: Optional[str] = None
    provider: CredentialProvider
    name: str
    api_key_masked: Optional[str] = None  # Solo para respuestas
    base_url: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApiCredentialCreate(BaseModel):
    """Modelo para crear/actualizar credenciales."""
    provider: CredentialProvider
    name: str
    api_key: str  # Plain text, will be encrypted
    base_url: Optional[str] = None
    is_default: bool = False


class ApiCredentialUpdate(BaseModel):
    """Modelo para actualizar credenciales."""
    name: Optional[str] = None
    api_key: Optional[str] = None  # If provided, will be re-encrypted
    base_url: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


# === DATA ACCESS LAYER ===

class AdminRepository:
    """Repositorio para acceder a tablas administrativas en schema 'chatbot'."""

    def __init__(self, postgres_url: str | None = None):
        self.postgres_url = postgres_url or settings.postgres_url
        self._conn = None

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.postgres_url)
            self._conn.autocommit = False
        return self._conn

    # --- System Configs ---

    def get_config(self, key: str) -> Optional[SystemConfig]:
        """Obtiene una configuración por clave."""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM chatbot.system_configs WHERE key = %s",
                    (key,)
                )
                row = cur.fetchone()
                return SystemConfig(**row) if row else None
        except Exception as e:
            logger.error(f"Error getting config {key}", error=str(e))
            return None

    def get_all_configs(self) -> list[SystemConfig]:
        """Obtiene todas las configuraciones."""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM chatbot.system_configs ORDER BY key")
                rows = cur.fetchall()
                return [SystemConfig(**row) for row in rows]
        except Exception as e:
            logger.error("Error getting all configs", error=str(e))
            return []

    def set_config(self, key: str, update: SystemConfigUpdate) -> bool:
        """Crea o actualiza una configuración."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chatbot.system_configs (key, value, description, updated_by, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        description = COALESCE(EXCLUDED.description, chatbot.system_configs.description),
                        updated_by = EXCLUDED.updated_by,
                        updated_at = NOW()
                    """,
                    (key, update.value, update.description, update.updated_by)
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting config {key}", error=str(e))
            if conn: conn.rollback()
            return False

    # --- Prompt Templates ---

    def get_prompt_template(self, name: str) -> Optional[PromptTemplate]:
        """Obtiene la plantilla activa por nombre."""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM chatbot.prompt_templates WHERE name = %s AND is_active = TRUE",
                    (name,)
                )
                row = cur.fetchone()
                return PromptTemplate(**row) if row else None
        except Exception as e:
            logger.error(f"Error getting prompt template {name}", error=str(e))
            return None
            
    def list_prompt_templates(self) -> list[PromptTemplate]:
        """Lista todas las plantillas activas."""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM chatbot.prompt_templates WHERE is_active = TRUE ORDER BY name")
                rows = cur.fetchall()
                return [PromptTemplate(**row) for row in rows]
        except Exception as e:
            logger.error("Error listing prompt templates", error=str(e))
            return []

    def upsert_prompt_template(self, data: PromptTemplateCreate) -> bool:
        """
        Crea o actualiza una plantilla.
        Nota: Incrementa versión automáticamente si ya existe.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Verificar si existe para incrementar versión
                cur.execute("SELECT version FROM chatbot.prompt_templates WHERE name = %s", (data.name,))
                row = cur.fetchone()
                new_version = (row[0] + 1) if row else 1
                
                cur.execute(
                    """
                    INSERT INTO chatbot.prompt_templates (name, content, version, description, updated_by, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (name) DO UPDATE SET
                        content = EXCLUDED.content,
                        version = chatbot.prompt_templates.version + 1,
                        description = COALESCE(EXCLUDED.description, chatbot.prompt_templates.description),
                        updated_by = EXCLUDED.updated_by,
                        updated_at = NOW()
                    """,
                    (data.name, data.content, new_version, data.description, data.updated_by)
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error upserting prompt template {data.name}", error=str(e))
            if conn: conn.rollback()
            return False

    # --- API Credentials ---

    def list_credentials(self, provider: Optional[CredentialProvider] = None) -> list[ApiCredential]:
        """Lista todas las credenciales (con API keys enmascaradas)."""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if provider:
                    cur.execute(
                        "SELECT * FROM chatbot.api_credentials WHERE provider = %s ORDER BY is_default DESC, name",
                        (provider.value,)
                    )
                else:
                    cur.execute("SELECT * FROM chatbot.api_credentials ORDER BY provider, is_default DESC, name")
                rows = cur.fetchall()
                
                credentials = []
                for row in rows:
                    try:
                        decrypted = decrypt_api_key(row['api_key_encrypted'])
                        masked = mask_api_key(decrypted)
                    except:
                        masked = "****"
                    
                    credentials.append(ApiCredential(
                        id=str(row['id']),
                        provider=row['provider'],
                        name=row['name'],
                        api_key_masked=masked,
                        base_url=row.get('base_url'),
                        is_default=row['is_default'],
                        is_active=row['is_active'],
                        last_used_at=row.get('last_used_at'),
                        created_at=row.get('created_at'),
                        updated_at=row.get('updated_at'),
                    ))
                return credentials
        except Exception as e:
            logger.error("Error listing credentials", error=str(e))
            return []

    def get_credential(self, credential_id: str) -> Optional[ApiCredential]:
        """Obtiene una credencial por ID (con key enmascarada)."""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM chatbot.api_credentials WHERE id = %s", (credential_id,))
                row = cur.fetchone()
                if not row:
                    return None
                
                try:
                    decrypted = decrypt_api_key(row['api_key_encrypted'])
                    masked = mask_api_key(decrypted)
                except:
                    masked = "****"
                
                return ApiCredential(
                    id=str(row['id']),
                    provider=row['provider'],
                    name=row['name'],
                    api_key_masked=masked,
                    base_url=row.get('base_url'),
                    is_default=row['is_default'],
                    is_active=row['is_active'],
                    last_used_at=row.get('last_used_at'),
                    created_at=row.get('created_at'),
                    updated_at=row.get('updated_at'),
                )
        except Exception as e:
            logger.error(f"Error getting credential {credential_id}", error=str(e))
            return None

    def get_default_credential(self, provider: CredentialProvider) -> Optional[tuple[str, str]]:
        """
        Obtiene la credencial default para un provider.
        Returns: (api_key_decrypted, base_url) or None
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT api_key_encrypted, base_url FROM chatbot.api_credentials 
                       WHERE provider = %s AND is_default = TRUE AND is_active = TRUE""",
                    (provider.value,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                
                decrypted = decrypt_api_key(row['api_key_encrypted'])
                return (decrypted, row.get('base_url'))
        except Exception as e:
            logger.error(f"Error getting default credential for {provider}", error=str(e))
            return None

    def create_credential(self, data: ApiCredentialCreate) -> Optional[str]:
        """Crea una nueva credencial. Returns credential ID."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Si es default, quitar default de otras del mismo provider
                if data.is_default:
                    cur.execute(
                        "UPDATE chatbot.api_credentials SET is_default = FALSE WHERE provider = %s",
                        (data.provider.value,)
                    )
                
                new_id = str(uuid.uuid4())
                encrypted_key = encrypt_api_key(data.api_key)
                
                cur.execute(
                    """INSERT INTO chatbot.api_credentials 
                       (id, provider, name, api_key_encrypted, base_url, is_default, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                    (new_id, data.provider.value, data.name, encrypted_key, data.base_url, data.is_default)
                )
            conn.commit()
            return new_id
        except Exception as e:
            logger.error(f"Error creating credential", error=str(e))
            if conn: conn.rollback()
            return None

    def update_credential(self, credential_id: str, data: ApiCredentialUpdate) -> bool:
        """Actualiza una credencial existente."""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get current provider for default handling
                cur.execute("SELECT provider FROM chatbot.api_credentials WHERE id = %s", (credential_id,))
                row = cur.fetchone()
                if not row:
                    return False
                provider = row['provider']
                
                # Build update query dynamically
                updates = []
                values = []
                
                if data.name is not None:
                    updates.append("name = %s")
                    values.append(data.name)
                if data.api_key is not None:
                    updates.append("api_key_encrypted = %s")
                    values.append(encrypt_api_key(data.api_key))
                if data.base_url is not None:
                    updates.append("base_url = %s")
                    values.append(data.base_url)
                if data.is_active is not None:
                    updates.append("is_active = %s")
                    values.append(data.is_active)
                if data.is_default is not None:
                    if data.is_default:
                        # Remove default from others first
                        cur.execute(
                            "UPDATE chatbot.api_credentials SET is_default = FALSE WHERE provider = %s AND id != %s",
                            (provider, credential_id)
                        )
                    updates.append("is_default = %s")
                    values.append(data.is_default)
                
                if not updates:
                    return True
                
                updates.append("updated_at = NOW()")
                values.append(credential_id)
                
                cur.execute(
                    f"UPDATE chatbot.api_credentials SET {', '.join(updates)} WHERE id = %s",
                    values
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating credential {credential_id}", error=str(e))
            if conn: conn.rollback()
            return False

    def delete_credential(self, credential_id: str) -> bool:
        """Elimina una credencial."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chatbot.api_credentials WHERE id = %s", (credential_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting credential {credential_id}", error=str(e))
            if conn: conn.rollback()
            return False

    def mark_credential_used(self, credential_id: str) -> None:
        """Actualiza timestamp de último uso."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE chatbot.api_credentials SET last_used_at = NOW() WHERE id = %s",
                    (credential_id,)
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Error marking credential used {credential_id}", error=str(e))

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()


# Instancia global
admin_repo = AdminRepository()

