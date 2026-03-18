"""
Nodos de escalamiento.

Clasifica si la conversación necesita atención humana
y ejecuta el proceso de escalamiento si es necesario.
"""

from typing import Any, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config.constants import EscalationMessages, EscalationResponse
from src.config.prompts import CLASSIFIER_PROMPT
from src.config.settings import settings
from src.models.state import ChatbotState
from src.nodes.decorators import handle_node_errors
from src.utils.logger import get_logger

logger = get_logger(__name__)


@handle_node_errors("classify_escalation")
async def classify_escalation(state: ChatbotState) -> ChatbotState:
    """
    Clasifica si la conversación requiere escalamiento humano.

    Corresponde al nodo 'Text Classifier' del workflow de n8n.
    Analiza el chat_input para determinar si se necesita
    intervención humana.

    Args:
        state: Estado actual del grafo

    Returns:
        Estado con needs_escalation actualizado
    """
    chat_input = state.get("chat_input", "")
    ai_response = state.get("ai_response", "")

    if state.get("gating_escalate"):
        state["needs_escalation"] = True
        state["escalation_reason"] = "Escalamiento forzado por CRM"
        state["_node_metrics"] = {
            "provider": None,
            "model_id": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        return state
    if not chat_input:
        state["needs_escalation"] = False
        return state

    logger.debug("Clasificando necesidad de escalamiento")

    try:
        llm: Any
        if settings.openai_api_key:
            llm = ChatOpenAI(
                model="openai/gpt-4.1-mini",
                api_key=SecretStr(settings.openai_api_key),
                base_url=settings.openai_base_url,
                temperature=0.0,
            )
        elif settings.google_api_key:
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.google_api_key,
                temperature=0.0,
            )
        else:
            state["needs_escalation"] = False
            return state

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CLASSIFIER_PROMPT),
                (
                    "human",
                    """
Mensaje del usuario:
{chat_input}

Respuesta del bot:
{ai_response}

¿Requiere atención humana? Responde SOLO "SI" o "NO".
""",
                ),
            ]
        )

        chain = prompt | llm

        response = await chain.ainvoke(
            {
                "chat_input": chat_input,
                "ai_response": ai_response,
            }
        )

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
                or usage.get("input_token_count")
            )
            output_tokens = (
                usage.get("output_tokens")
                or usage.get("completion_tokens")
                or usage.get("candidates_token_count")
                or usage.get("output_token_count")
            )
            total_tokens = usage.get("total_tokens") or usage.get("total_token_count")
        else:
            try:
                prompt_text = f"{chat_input}\n{ai_response}"
                approx = int(len(prompt_text) / 4)
                input_tokens = int(len(chat_input or "") / 4)
                output_tokens = approx - (input_tokens or 0)
            except Exception:
                input_tokens = None
                output_tokens = None
        if total_tokens is None and (input_tokens is not None or output_tokens is not None):
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        provider = (
            "openrouter"
            if settings.openai_api_key
            else ("gemini" if settings.google_api_key else None)
        )
        model_id = None
        if provider == "openrouter":
            model_id = "openai/gpt-4.1-mini"
        elif provider == "gemini":
            model_id = "gemini-1.5-flash"

        state["_node_metrics"] = {
            "provider": provider,
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": None,
        }

        content = response.content
        if isinstance(content, str):
            result = content.strip().upper()
        elif isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    t = item.get("text")
                    if isinstance(t, str):
                        parts.append(t)
            result = " ".join(parts).strip().upper()
        else:
            result = str(content).strip().upper()
        needs_escalation = result == "SI" or result == "SÍ"

        state["needs_escalation"] = needs_escalation

        logger.info(
            "Clasificación de escalamiento completada",
            needs_escalation=needs_escalation,
            raw_result=result,
        )

    except Exception as e:
        logger.error("Error en clasificación", error=str(e))
        state["needs_escalation"] = False

    return state


def route_escalation(state: ChatbotState) -> Literal["escalate", "continue"]:
    """
    Routing basado en la clasificación de escalamiento.

    Returns:
        "escalate" si necesita humano, "continue" si no
    """
    return "escalate" if state.get("needs_escalation", False) else "continue"


async def escalate_to_human(state: ChatbotState) -> ChatbotState:
    """
    Ejecuta el proceso de escalamiento a humano.

    Corresponde a los nodos 'etiqueta_asistencia_ia' y 'apagar bot'.

    1. Agrega etiqueta a la conversación
    2. Desactiva el bot para este usuario
    3. (Opcional) Envía notificación por email

    Args:
        state: Estado actual del grafo

    Returns:
        Estado sin modificaciones significativas
    """
    conversation_id = state.get("conversation_id", 0)
    contact_id = state.get("contact_id", 0)
    state.get("phone_number", "")

    logger.info(
        "Iniciando escalamiento a humano",
        conversation_id=conversation_id,
        contact_id=contact_id,
    )

    try:
        state["needs_escalation"] = True
        if not state.get("escalation_reason"):
            state["escalation_reason"] = "Usuario requiere atención especializada"

        actions: dict[str, Any] = {}
        current_actions = state.get("actions")
        if isinstance(current_actions, dict):
            actions.update(current_actions)

        labels: list[str] = []
        raw_labels = actions.get("apply_labels")
        if isinstance(raw_labels, list):
            labels = [x for x in raw_labels if isinstance(x, str)]
        for lb in ["asistencia_ia", "escalado"]:
            if lb not in labels:
                labels.append(lb)
        actions["apply_labels"] = labels
        actions["set_ia_state"] = "OFF"
        actions["send_message"] = (
            "Te estoy conectando con uno de nuestros agentes. Por favor espera un momento."
        )
        state["actions"] = actions

        logger.info("Escalamiento marcado para ejecución externa", conversation_id=conversation_id)

    except Exception as e:
        logger.error(
            "Error durante escalamiento",
            error=str(e),
            conversation_id=conversation_id,
        )
        state["error"] = f"Escalation error: {str(e)}"

    return state
