"""
Prompts del sistema para el chatbot.

Centraliza la lógica para construir el System Prompt dinámicamente basado en:
1. Core Prompt (Reglas Globales)
2. Vertical Prompt (Reglas de Nicho)
3. Tenant Prompt (Datos del Negocio)
"""

from src.prompts.core.system import CORE_SYSTEM_PROMPT
from src.prompts.tenants.template import build_tenant_prompt
from src.prompts.verticals.ecommerce import ECOMMERCE_VERTICAL_PROMPT
from src.prompts.verticals.optics import OPTICS_VERTICAL_PROMPT
from src.prompts.verticals.restaurant import RESTAURANT_VERTICAL_PROMPT

# =============================================================================
# MAPA DE VERTICALES
# =============================================================================
VERTICAL_MAP = {
    "restaurante": RESTAURANT_VERTICAL_PROMPT,
    "ecommerce": ECOMMERCE_VERTICAL_PROMPT,
    "optica": OPTICS_VERTICAL_PROMPT,
    # Fallback por defecto
    "default": RESTAURANT_VERTICAL_PROMPT
}

# =============================================================================
# SYSTEM PROMPT FACTORY 🏭
# =============================================================================

def get_system_prompt(vertical_id: str, tenant_data: dict) -> str:
    """
    Construye el System Prompt final combinando capas.
    Intenta cargar desde DB primero, con fallback a archivos estáticos.
    """
    try:
        from src.models.admin import admin_repo
        
        # 1. Intentar cargar Vertical Prompt de DB
        vertical_template_name = f"{vertical_id}_vertical_prompt"
        db_vertical = admin_repo.get_prompt_template(vertical_template_name)
        
        if db_vertical:
            vertical_prompt = db_vertical.content
        else:
            # Fallback a archivo
            vertical_prompt = VERTICAL_MAP.get(vertical_id.lower(), VERTICAL_MAP["default"])

        # 2. Construir Tenant Prompt (Hidratación de datos)
        # TODO: Cargar template de tenant desde DB si existe
        tenant_prompt = build_tenant_prompt(tenant_data)

        # 3. Intentar cargar Core Prompt de DB
        db_core = admin_repo.get_prompt_template("core_system_prompt")
        core_prompt = db_core.content if db_core else CORE_SYSTEM_PROMPT

        # 4. Ensamblaje Final
        final_prompt = f"""
{tenant_prompt}

{vertical_prompt}

{core_prompt}
"""
        return final_prompt.strip()

    except Exception as e:
        # Fallback de seguridad total: usar estáticos si falla la DB
        # logger.error(f"Error loading dynamic prompts: {e}")
        vertical_prompt = VERTICAL_MAP.get(vertical_id.lower(), VERTICAL_MAP["default"])
        tenant_prompt = build_tenant_prompt(tenant_data)
        return f"{tenant_prompt}\n\n{vertical_prompt}\n\n{CORE_SYSTEM_PROMPT}".strip()

# =============================================================================
# MOCK DATA (Para desarrollo/tests locales)
# =============================================================================
_MOCK_TENANT_DATA = {
    "nombre": "Pizzería Don Mario (DEV)",
    "giro": "Pizzería Artesanal",
    "ubicacion": "Localhost via Ngrok",
    "horarios": "24/7 en Dev Mode",
    "reglas_reserva": "Sin reglas en dev.",
    "delivery_info": "Simulado.",
    "metodos_pago": "Visa, MockMoney.",
    "reglas": "- Entorno de pruebas.",
    "tono": "- Robot servicial de pruebas.",
    "oferta": "Pizzas binarias."
}

# Para compatibilidad con código legado que importe BUSINESS_PROMPT directamente
# TODO: Refactorizar dependencias para usar get_system_prompt()
BUSINESS_PROMPT = get_system_prompt("restaurante", _MOCK_TENANT_DATA)


# =============================================================================
# PROMPT DEL FORMATEADOR
# =============================================================================
FORMATTER_PROMPT = """
## Rol
Eres un formateador de salidas para WhatsApp.

## Objetivo
Toma el texto de la entrada y devuélvelo en formato JSON.
SOLO divide en múltiples partes si el mensaje es realmente largo (más de 200 caracteres).
Para mensajes cortos, usa SOLO part_1.

## Reglas Críticas
1. Mensajes cortos (menos de 200 caracteres): USA SOLO part_1, deja part_2 y part_3 vacías ("")
2. Mensajes largos (más de 200 caracteres): Divide lógicamente en 2-3 partes máximo
3. part_1 debe contener siempre texto
4. part_2 y part_3 deben estar vacías ("") si no son necesarias
5. Cada parte máximo 3 frases cortas
6. Idioma: Español de Latinoamérica
7. Elimina caracteres: *, ¿, ¡, #
8. Elimina saltos de línea innecesarios
9. NO añadas, quites ni reordenes información
10. NUNCA envíes texto fuera del JSON

## Formato de Salida
{
  "part_1": "Primera parte del mensaje (siempre requerida)",
  "part_2": "Segunda parte (opcional, vacía si no es necesaria)",
  "part_3": "Tercera parte (opcional, vacía si no es necesaria)"
}
"""

# =============================================================================
# PROMPT DEL CLASIFICADOR DE ESCALAMIENTO
# =============================================================================
CLASSIFIER_PROMPT = """
## Rol
Eres un clasificador que analiza mensajes de clientes en una conversación con un bot.

## Objetivo
Determinar si el mensaje requiere intervención humana urgente.

## Clasificar como "SI" (requiere humano) cuando:
1. El cliente expresa frustración o enojo extremo
2. Hay un problema médico o de seguridad
3. El cliente solicita explícitamente hablar con un humano
4. La consulta es demasiado compleja para el bot
5. El cliente tiene una queja seria sobre productos/servicios
6. Hay información sensible que requiere manejo humano

## Clasificar como "NO" (el bot puede continuar) cuando:
1. La conversación fluye normalmente
2. Las preguntas son rutinarias
3. El cliente parece satisfecho con las respuestas
4. No hay señales de urgencia

## Respuesta
Responde ÚNICAMENTE con "SI" o "NO", sin explicación adicional.
"""

# =============================================================================
# PROMPT DE ANÁLISIS DE IMAGEN
# =============================================================================
IMAGE_ANALYSIS_PROMPT = """
Analiza detalladamente esta imagen. Identifica:

1. Tipo de contenido principal (producto, documento, foto personal, etc.)
2. Texto visible en la imagen (si hay)
3. Elementos relevantes para atención al cliente
4. Cualquier información que pueda ser útil para responder al cliente

Sé específico y preciso en tu descripción.
Responde en español.
"""
