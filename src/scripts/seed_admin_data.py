"""
Script para poblar la base de datos administrativa con datos iniciales.
Usa los modelos y repositorios definidos en src.models.admin y los prompts
existentes en el código como fuente de verdad inicial.
"""

import sys
import os

# Asegurar que el directorio raíz está en PYTHONPATH
sys.path.append(os.getcwd())

from src.models.admin import admin_repo, SystemConfigUpdate, PromptTemplateCreate
from src.config.prompts import CORE_SYSTEM_PROMPT, VERTICAL_MAP, FORMATTER_PROMPT, CLASSIFIER_PROMPT, IMAGE_ANALYSIS_PROMPT
from src.utils.logger import get_logger

logger = get_logger(__name__)

def seed_configs():
    """Poblar configuraciones del sistema."""
    logger.info("Seeding System Configs...")
    
    configs = [
        {
            "key": "llm_model",
            "value": "openai/gpt-4o-mini",
            "description": "Modelo LLM principal para el agente."
        },
        {
            "key": "llm_temperature",
            "value": "0.0",
            "description": "Temperatura para el sampling del LLM (0.0 = determinista)."
        },
        {
            "key": "openai_api_key",
            "value": "", # Dejar vacío o poner un placeholder, es secreto
            "description": "API Key de OpenAI (opcional, sobreescribe ENV).",
            # Nota: El modelo actual no soporta 'is_secret' en SystemConfigUpdate explícitamente en el repo
            # pero el modelo DB sí lo tiene. Por ahora solo seteamos value.
        }
    ]

    for conf in configs:
        update = SystemConfigUpdate(
            value=conf["value"],
            description=conf["description"],
            updated_by="system_seeder"
        )
        if admin_repo.set_config(conf["key"], update):
            logger.info(f"✅ Config '{conf['key']}' set/updated.")
        else:
            logger.error(f"❌ Failed to set config '{conf['key']}'.")

def seed_prompts():
    """Poblar plantillas de prompts."""
    logger.info("Seeding Prompt Templates...")

    prompts_to_seed = []

    # 1. Core System Prompt
    prompts_to_seed.append({
        "name": "core_system_prompt",
        "content": CORE_SYSTEM_PROMPT,
        "description": "Prompt base del sistema (reglas globales)."
    })

    # 2. Vertical Prompts
    for vertical_id, content in VERTICAL_MAP.items():
        if vertical_id == "default": 
            continue # Skip default key as it's just a reference
            
        prompts_to_seed.append({
            "name": f"{vertical_id}_vertical_prompt",
            "content": content,
            "description": f"Prompt específico para la vertical: {vertical_id.capitalize()}."
        })

    # 3. Other Utility Prompts
    prompts_to_seed.append({
        "name": "formatter_prompt",
        "content": FORMATTER_PROMPT,
        "description": "Prompt para el formateador de salidas JSON."
    })
    
    prompts_to_seed.append({
        "name": "classifier_prompt",
        "content": CLASSIFIER_PROMPT,
        "description": "Prompt para clasificar escalamiento humano."
    })

    prompts_to_seed.append({
        "name": "image_analysis_prompt",
        "content": IMAGE_ANALYSIS_PROMPT,
        "description": "Prompt para análisis de imágenes (visión)."
    })

    for p in prompts_to_seed:
        create_data = PromptTemplateCreate(
            name=p["name"],
            content=p["content"],
            description=p["description"],
            updated_by="system_seeder"
        )
        if admin_repo.upsert_prompt_template(create_data):
            logger.info(f"✅ Prompt '{p['name']}' upserted.")
        else:
            logger.error(f"❌ Failed to upsert prompt '{p['name']}'.")

def main():
    logger.info("🌱 Starting Admin Data Seeding...")
    try:
        seed_configs()
        seed_prompts()
        logger.info("🌱 Seeding completed successfully.")
    except Exception as e:
        logger.error(f"💥 Seeding crashed: {e}")
    finally:
        admin_repo.close()

if __name__ == "__main__":
    main()
