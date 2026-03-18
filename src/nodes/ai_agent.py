"""
Nodo del agente de IA.

Genera respuestas usando LangChain con GPT-4o-mini via OpenRouter.
Incluye memoria conversacional por usuario.

ARQUITECTURA REFACTORIZADA:
- Flujo determinista de una sola invocación (sin doble llamada LLM)
- Contexto de memoria inyectado directamente en el prompt
- RAG bajo demanda solo si se detecta necesidad
- Parsing JSON robusto con múltiples fallbacks
"""

import json as _json
import re
from datetime import datetime
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config.constants import ErrorMessages
from src.config.prompts import get_system_prompt
from src.config.settings import settings
from src.memory.conversation_memory import conversation_memory
from src.memory.semantic_memory import maybe_enqueue_episode, upsert_episode
from src.models.state import ChatbotState
from src.nodes.decorators import handle_node_errors
from src.nodes.tools import inventory_lookup, rag_search, semantic_memory_search
from src.utils.logger import get_logger
from src.utils.text import escape_curly

logger = get_logger(__name__)


def _parse_llm_json(content: str) -> dict[str, Any]:
    """
    Parsea JSON del LLM con múltiples estrategias de fallback.
    
    Returns:
        Diccionario parseado o fallback con response_text
    """
    if not content or not content.strip():
        return _create_fallback_response("")
    
    clean = content.strip()
    
    # Estrategia 1: Remover bloques de código markdown
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*\n?", "", clean)
        clean = re.sub(r"\n?```\s*$", "", clean)
        clean = clean.strip()
    
    # Estrategia 2: Buscar primer objeto JSON válido
    try:
        return _json.loads(clean)
    except _json.JSONDecodeError:
        pass
    
    # Estrategia 3: Buscar JSON entre llaves
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        try:
            return _json.loads(clean[start:end + 1])
        except _json.JSONDecodeError:
            pass
    
    # Fallback: Usar el contenido como response_text
    return _create_fallback_response(content)


def _create_fallback_response(content: str) -> dict[str, Any]:
    """Crea respuesta de fallback cuando el parsing JSON falla."""
    return {
        "response_text": content if content else "Lo siento, tuve un problema procesando mi respuesta.",
        "requires_human": False,
        "nlu": {"intent": "unknown", "confidence": 0.0},
        "suggested_actions": {}
    }





@handle_node_errors("generate_response", fallback_response=ErrorMessages.GENERIC)
async def generate_response(state: ChatbotState) -> ChatbotState:
    """
    Genera una respuesta usando el agente de IA.

    Flujo simplificado:
    1. Construir prompt con contexto completo (sistema + usuario + memoria)
    2. Opcionalmente agregar documentos RAG si se detecta necesidad
    3. Una sola invocación del LLM
    4. Parsing robusto del JSON de respuesta

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con ai_response poblado
    """
    # === 1. EXTRAER DATOS DEL CONTEXTO ===
    chat_input = state.get("chat_input", "")
    info_imagen = state.get("info_imagen")
    phone_number = state.get("phone_number", "")
    identifier = state.get("namespaced_id") or state.get("identifier", "")
    user_name = state.get("user_name", "Cliente")

    if not chat_input:
        logger.warning("No hay chat_input para generar respuesta")
        state["ai_response"] = "Lo siento, no pude procesar tu mensaje."
        return state

    # === 2. CONSTRUIR SYSTEM PROMPT ===
    vertical_id = state.get("vertical_id", "restaurante")
    tenant_data = state.get("tenant_data", {})
    system_message = state.get("system_prompt") or get_system_prompt(vertical_id, tenant_data)
    state["system_prompt"] = system_message

    logger.info(
        "Generando respuesta con IA",
        chat_input_length=len(chat_input),
        has_image_info=bool(info_imagen),
    )

    try:
        # === 3. CONFIGURAR LLM (DINÁMICO) ===
        from src.models.admin import admin_repo
        
        # Obtener configuración dinámica o usar defaults
        model_config = admin_repo.get_config("llm_model")
        temp_config = admin_repo.get_config("llm_temperature")
        
        model_id = model_config.value if model_config else "openai/gpt-4o-mini"
        
        _t = state.get("temperature")
        if _t is not None:
            temperature = float(_t)
        elif temp_config:
            temperature = float(temp_config.value)
        else:
            temperature = 0.7

        _mt = state.get("max_tokens")
        max_tokens = _mt if isinstance(_mt, int) and _mt > 0 else None
        mk = {"max_tokens": max_tokens} if isinstance(max_tokens, int) else {}
        
        # Log si estamos usando config dinámica
        if model_config:
            logger.debug(f"Using dynamic model: {model_id} (temp={temperature})")
        
        llm = ChatOpenAI(
            model=model_id,
            api_key=SecretStr(settings.openai_api_key),
            base_url=settings.openai_base_url,
            temperature=temperature,
            model_kwargs=mk,
        )

        # === 4. CONSTRUIR CONTEXTO DEL USUARIO ===
        tenant_id = state.get("tenant_id")
        tenant_slug = state.get("tenant_slug")
        
        user_context = f"""## Contexto del Usuario
- Nombre: {user_name}
- Número: {phone_number}
- Tenant ID: {tenant_id}
- Tenant Slug: {tenant_slug}

## Mensaje del Usuario
{chat_input}
"""
        if info_imagen:
            user_context += f"""
## Información de Imagen Analizada
{info_imagen}
"""

        # === 5. INYECTAR MEMORIA CONVERSACIONAL ===
        messages: list[tuple[str, str]] = [
            ("system", escape_curly(system_message)),
            ("human", escape_curly(user_context)),
        ]
        
        # Agregar historial de conversación
        try:
            max_turns = 2 * int(settings.memory_window_size or 4)
            history = await conversation_memory.get_history(identifier)
            if history:
                context_data = {"tool": "get_context_window", "result": {"messages": history[-max_turns:]}}
                context_block = _json.dumps(context_data, ensure_ascii=False)
                messages.append(("system", f"## Historial de Conversación\n{escape_curly(context_block)}"))
        except Exception as e:
            logger.debug("No se pudo cargar historial", error=str(e))

        # === 6. CONFIGURAR TOOLS Y LLM ===
        tools = [rag_search, inventory_lookup, semantic_memory_search]
        llm_with_tools = llm.bind_tools(tools)

        # === 7. PRIMERA INVOCACIÓN ===
        # Nota: messages ya contiene tuplas, necesitamos convertirlas a objetos Message si vamos a appendear
        # LangChain maneja mezcla, pero para el tool loop es mejor ser explícitos
        # Sin embargo, ainvoke soporta lista de tuplas.
        
        # Invocación inicial
        response = await llm_with_tools.ainvoke(messages)
        
        # === 8. PROCESAR TOOL CALLS (Loop simple de 1 paso) ===
        if response.tool_calls:
            # Convertir historial previo a objetos message para poder appendear consistente
            chat_template = ChatPromptTemplate.from_messages(messages)
            current_messages = chat_template.format_messages()
            
            # Agregar la respuesta del asistente con la intención de llamada
            current_messages.append(response)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                args = tool_call["args"]
                call_id = tool_call["id"]
                
                # Inyectar contextos implícitos si faltan
                if "tenant_id" not in args:
                    args["tenant_id"] = str(tenant_id or "")
                    
                if tool_name == "inventory_lookup" and "sheet_id" not in args:
                    sid = state.get("google_sheet_id")
                    if not sid:
                        sid = tenant_data.get("google_sheet_id")
                    args["sheet_id"] = str(sid or "")
                    
                if tool_name == "semantic_memory_search" and "identifier" not in args:
                    args["identifier"] = str(identifier)
                
                logger.info(f"🤖 Tool Call: {tool_name}", args=args)
                
                try:
                    tool_result = "Herramienta no encontrada"
                    if tool_name == "rag_search":
                        tool_result = await rag_search.ainvoke(args)
                    elif tool_name == "inventory_lookup":
                        tool_result = await inventory_lookup.ainvoke(args)
                    elif tool_name == "semantic_memory_search":
                        tool_result = await semantic_memory_search.ainvoke(args)
                    
                    # Agregar resultado
                    current_messages.append(ToolMessage(content=str(tool_result), tool_call_id=call_id))
                    
                except Exception as e:
                    logger.error(f"Error executing {tool_name}", error=str(e))
                    current_messages.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=call_id))
            
            # === 9. SEGUNDA INVOCACIÓN (CON RESULTADOS) ===
            response = await llm_with_tools.ainvoke(current_messages)
        content_raw = response.content if isinstance(response.content, str) else str(response.content)

        # === 10. PARSEAR RESPUESTA JSON ===
        parsed_json = _parse_llm_json(content_raw)

        # Extraer campos
        response_text = parsed_json.get("response_text", "")
        if not response_text and "response" in parsed_json:
            response_text = parsed_json["response"]
        if not response_text:
            response_text = "Lo siento, tuve un problema interno procesando la respuesta."

        requires_human = parsed_json.get("requires_human", False)
        nlu_data = parsed_json.get("nlu", {})
        actions_data = parsed_json.get("suggested_actions", {})

        # === 11. ACTUALIZAR ESTADO ===
        state["ai_response"] = response_text
        
        # Preservar datos existentes de NLU si el agente no devolvió datos válidos
        existing_nlu = state.get("nlu", {})
        if isinstance(nlu_data, dict) and nlu_data.get("intent") not in (None, "unknown"):
            state["nlu"] = nlu_data
        elif isinstance(existing_nlu, dict) and existing_nlu:
            # Mantener NLU previo del nodo classify_intent
            pass
        else:
            state["nlu"] = nlu_data
            
        # Merge actions en lugar de sobrescribir
        existing_actions = state.get("actions", {})
        merged_actions = {}
        if isinstance(existing_actions, dict):
            merged_actions.update(existing_actions)
        if isinstance(actions_data, dict):
            merged_actions.update(actions_data)
        state["actions"] = merged_actions

        if requires_human:
            state["needs_escalation"] = True
            state["escalation_reason"] = parsed_json.get("escalation_reason", "model_flagged")

        # === 12. MÉTRICAS DE TOKENS ===
        usage = None
        try:
            usage = getattr(response, "usage_metadata", None)
            if not usage and hasattr(response, "response_metadata"):
                meta = response.response_metadata or {}
                usage = meta.get("token_usage") or meta.get("usage")
        except Exception:
            usage = None

        input_tokens = None
        output_tokens = None
        total_tokens = None
        
        if isinstance(usage, dict):
            input_tokens = (
                usage.get("input_tokens")
                or usage.get("prompt_tokens")
                or usage.get("prompt_token_count")
            )
            output_tokens = (
                usage.get("output_tokens")
                or usage.get("completion_tokens")
                or usage.get("candidates_token_count")
            )
            total_tokens = usage.get("total_tokens") or usage.get("total_token_count")
        
        if total_tokens is None and (input_tokens is not None or output_tokens is not None):
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        provider = "openrouter" if "openrouter" in settings.openai_base_url else "openai"
        state["_node_metrics"] = {
            "provider": provider,
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": None,
        }

        # === 13. PERSISTIR EN MEMORIA ===
        await conversation_memory.add_message(identifier, "user", str(chat_input))
        await conversation_memory.add_message(identifier, "assistant", response_text)

        # === 14. EPISODIOS SEMÁNTICOS ===
        try:
            empresa_id = str(state.get("tenant_id") or "")
            ident2 = str(state.get("namespaced_id") or state.get("identifier") or "")
            
            if settings.semantic_episode_inline_enabled:
                cur = state.get("current_message") or {}
                sid = cur.get("source_id") if isinstance(cur, dict) else None
                eid = str(sid or state.get("conversation_id") or datetime.now().timestamp())
                
                cs = None
                try:
                    ts = cur.get("created_at") if isinstance(cur, dict) else None
                    if isinstance(ts, str) and ts:
                        cs = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    pass
                
                summary_text = f"Usuario: {str(chat_input)}\nAsistente: {str(response_text)}"
                upsert_episode(empresa_id, ident2, eid, summary_text, cs, datetime.now())
            
            try:
                await maybe_enqueue_episode(empresa_id, ident2)
            except Exception:
                pass
        except Exception as e:
            logger.warning("Failed semantic episode operations", error=str(e))

        logger.info(
            "Respuesta generada exitosamente",
            response_length=len(response_text),
            intent=nlu_data.get("intent", "unknown") if isinstance(nlu_data, dict) else "unknown",
            requires_human=requires_human
        )

    except Exception as e:
        logger.error("Error en AI Agent", error=str(e), exc_info=True)
        state["ai_response"] = "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."
        state["error"] = str(e)

    return state
