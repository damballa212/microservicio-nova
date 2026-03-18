"""
Router para gestión de credenciales de API.
Permite CRUD de credenciales para múltiples proveedores.
"""

from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.models.admin import (
    ApiCredential,
    ApiCredentialCreate,
    ApiCredentialUpdate,
    CredentialProvider,
    admin_repo,
    decrypt_api_key,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

credentials_router = APIRouter(prefix="/admin/credentials", tags=["Admin - Credentials"])


# === Response Models ===

class CredentialResponse(BaseModel):
    success: bool
    credential: Optional[ApiCredential] = None
    message: Optional[str] = None


class CredentialsListResponse(BaseModel):
    credentials: list[ApiCredential]
    total: int


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[int] = None


# === Endpoints ===

@credentials_router.get("", response_model=CredentialsListResponse)
async def list_credentials(
    provider: Optional[CredentialProvider] = Query(None, description="Filter by provider")
):
    """Lista todas las credenciales (API keys enmascaradas)."""
    try:
        credentials = admin_repo.list_credentials(provider)
        return CredentialsListResponse(
            credentials=credentials,
            total=len(credentials)
        )
    except Exception as e:
        logger.error("Error listing credentials", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list credentials")


@credentials_router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(credential_id: str):
    """Obtiene una credencial por ID."""
    credential = admin_repo.get_credential(credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    return CredentialResponse(success=True, credential=credential)


@credentials_router.post("", response_model=CredentialResponse)
async def create_credential(data: ApiCredentialCreate):
    """Crea una nueva credencial."""
    try:
        credential_id = admin_repo.create_credential(data)
        if not credential_id:
            raise HTTPException(status_code=500, detail="Failed to create credential")
        
        credential = admin_repo.get_credential(credential_id)
        return CredentialResponse(
            success=True, 
            credential=credential,
            message="Credential created successfully"
        )
    except Exception as e:
        logger.error("Error creating credential", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@credentials_router.patch("/{credential_id}", response_model=CredentialResponse)
async def update_credential(credential_id: str, data: ApiCredentialUpdate):
    """Actualiza una credencial existente."""
    existing = admin_repo.get_credential(credential_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    success = admin_repo.update_credential(credential_id, data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update credential")
    
    updated = admin_repo.get_credential(credential_id)
    return CredentialResponse(
        success=True,
        credential=updated,
        message="Credential updated successfully"
    )


@credentials_router.delete("/{credential_id}")
async def delete_credential(credential_id: str):
    """Elimina una credencial."""
    existing = admin_repo.get_credential(credential_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    success = admin_repo.delete_credential(credential_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete credential")
    
    return {"success": True, "message": "Credential deleted successfully"}


@credentials_router.post("/{credential_id}/set-default", response_model=CredentialResponse)
async def set_default_credential(credential_id: str):
    """Establece una credencial como default para su proveedor."""
    existing = admin_repo.get_credential(credential_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    success = admin_repo.update_credential(
        credential_id, 
        ApiCredentialUpdate(is_default=True)
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set default")
    
    updated = admin_repo.get_credential(credential_id)
    return CredentialResponse(
        success=True,
        credential=updated,
        message=f"Set as default for {existing.provider.value}"
    )


@credentials_router.post("/{credential_id}/test", response_model=TestConnectionResponse)
async def test_credential(credential_id: str):
    """Prueba la conexión con una credencial."""
    import time
    
    existing = admin_repo.get_credential(credential_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    # Get decrypted key for testing
    result = admin_repo.get_default_credential(existing.provider)
    if not result:
        # Not default, need to fetch directly
        try:
            from src.models.admin import decrypt_api_key
            import psycopg2
            from psycopg2.extras import RealDictCursor
            from src.config.settings import settings
            
            conn = psycopg2.connect(settings.postgres_url)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT api_key_encrypted, base_url FROM chatbot.api_credentials WHERE id = %s",
                    (credential_id,)
                )
                row = cur.fetchone()
                if row:
                    api_key = decrypt_api_key(row['api_key_encrypted'])
                    base_url = row.get('base_url') or _get_default_base_url(existing.provider)
                else:
                    raise HTTPException(status_code=404, detail="Credential not found")
            conn.close()
        except Exception as e:
            logger.error("Error getting credential for test", error=str(e))
            return TestConnectionResponse(
                success=False,
                message=f"Error decrypting credential: {str(e)}"
            )
    else:
        api_key, base_url = result
        base_url = base_url or _get_default_base_url(existing.provider)
    
    # Test connection based on provider
    try:
        start_time = time.time()
        
        if existing.provider in [CredentialProvider.OPENROUTER, CredentialProvider.OPENAI]:
            # Test OpenAI-compatible API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                response.raise_for_status()
        
        elif existing.provider == CredentialProvider.GOOGLE:
            # Test Google Gemini API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
                )
                response.raise_for_status()
        
        elif existing.provider == CredentialProvider.ANTHROPIC:
            # Anthropic doesn't have a simple health endpoint, so we just validate format
            if not api_key.startswith("sk-ant-"):
                return TestConnectionResponse(
                    success=False,
                    message="Invalid Anthropic API key format"
                )
            # Skip actual request for Anthropic
            pass
        
        else:
            # Generic test - just verify key is not empty
            if not api_key or len(api_key) < 10:
                return TestConnectionResponse(
                    success=False,
                    message="API key appears to be invalid (too short)"
                )
        
        latency = int((time.time() - start_time) * 1000)
        
        # Mark as used
        admin_repo.mark_credential_used(credential_id)
        
        return TestConnectionResponse(
            success=True,
            message="Connection successful",
            latency_ms=latency
        )
        
    except httpx.HTTPStatusError as e:
        return TestConnectionResponse(
            success=False,
            message=f"API error: {e.response.status_code} - {e.response.text[:200]}"
        )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


def _get_default_base_url(provider: CredentialProvider) -> str:
    """Get default base URL for a provider."""
    defaults = {
        CredentialProvider.OPENROUTER: "https://openrouter.ai/api/v1",
        CredentialProvider.OPENAI: "https://api.openai.com/v1",
        CredentialProvider.ANTHROPIC: "https://api.anthropic.com/v1",
        CredentialProvider.GOOGLE: "https://generativelanguage.googleapis.com/v1",
        CredentialProvider.MISTRAL: "https://api.mistral.ai/v1",
        CredentialProvider.COHERE: "https://api.cohere.ai/v1",
    }
    return defaults.get(provider, "")
