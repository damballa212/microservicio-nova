from fastapi import APIRouter, HTTPException, Depends
from typing import List

from src.models.admin import (
    admin_repo, 
    SystemConfig, 
    SystemConfigUpdate, 
    PromptTemplate, 
    PromptTemplateCreate
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# TODO: Add authentication dependency here
# async def get_current_admin(token: str = Depends(...)): ...


# === CONFIGURATION ENDPOINTS ===

@router.get("/config", response_model=List[SystemConfig])
async def get_all_configs():
    """Obtiene todas las configuraciones del sistema."""
    return admin_repo.get_all_configs()

@router.get("/config/{key}", response_model=SystemConfig)
async def get_config(key: str):
    """Obtiene una configuración específica."""
    config = admin_repo.get_config(key)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@router.patch("/config/{key}", response_model=bool)
async def update_config(key: str, update: SystemConfigUpdate):
    """Actualiza una configuración."""
    # TODO: Get user from auth context
    update.updated_by = "admin_api" 
    
    success = admin_repo.set_config(key, update)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update config")
    
    logger.info(f"Config updated: {key} = {update.value} by {update.updated_by}")
    return True


# === PROMPT TEMPLATE ENDPOINTS ===

@router.get("/prompts", response_model=List[PromptTemplate])
async def list_prompts():
    """Lista todos los templates de prompts activos."""
    return admin_repo.list_prompt_templates()

@router.get("/prompts/{name}", response_model=PromptTemplate)
async def get_prompt(name: str):
    """Obtiene un template por nombre."""
    template = admin_repo.get_prompt_template(name)
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return template

@router.post("/prompts", response_model=bool)
async def upsert_prompt(data: PromptTemplateCreate):
    """
    Crea o actualiza un template de prompt.
    Incrementa automáticamente la versión si ya existe.
    """
    # TODO: Get user from auth context
    data.updated_by = "admin_api"
    
    success = admin_repo.upsert_prompt_template(data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save prompt template")
    
    logger.info(f"Prompt template upserted: {data.name} by {data.updated_by}")
    return True
