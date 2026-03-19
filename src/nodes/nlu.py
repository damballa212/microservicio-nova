import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config.settings import settings
from src.models.state import ChatbotState
from src.utils.logger import get_logger
from src.utils.text import escape_curly

logger = get_logger(__name__)


def _get_db_credentials() -> tuple[str | None, str | None]:
    """Obtiene API key y base_url del admin_repo (DB), con fallback a settings."""
    try:
        from src.models.admin import admin_repo, CredentialProvider
        cred = admin_repo.get_default_credential(CredentialProvider.OPENROUTER)
        if cred:
            key, base_url = cred
            return key, base_url or "https://openrouter.ai/api/v1"
    except Exception:
        pass
    return settings.openai_api_key or None, settings.openai_base_url or None


def _merge_actions(state: ChatbotState) -> dict[str, Any]:
    current = state.get("actions")
    if isinstance(current, dict):
        return dict(current)
    return {}


def _merge_labels(actions: dict[str, Any], new_labels: list[str]) -> list[str]:
    existing: list[str] = []
    raw = actions.get("apply_labels")
    if isinstance(raw, list):
        existing = [x for x in raw if isinstance(x, str)]
    out: list[str] = []
    seen: set[str] = set()
    for lb in existing + new_labels:
        s = (lb or "").strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _heuristic_intent(text: str, info_imagen: str | None) -> tuple[str, list[str]]:
    t = (text or "").lower()
    labels: list[str] = []
    intent = "consulta_general"

    if any(
        k in t
        for k in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches"]
    ):
        intent = "saludo"
        labels.append("saludo")

    if any(k in t for k in ["precio", "cuesta", "vale", "costo", "coste", "cuánto", "cuanto"]):
        intent = "consulta_precio"
        labels.append("consulta_precio")

    if any(
        k in t
        for k in ["disponible", "disponibilidad", "hay", "tienen", "stock", "queda", "quedan"]
    ):
        intent = "consulta_disponibilidad"
        labels.append("consulta_disponibilidad")

    if any(k in t for k in ["horario", "abren", "cierran", "abierto", "cerrado"]):
        intent = "consulta_horario"
        labels.append("consulta_horario")

    if any(
        k in t
        for k in [
            "direccion",
            "dirección",
            "ubicacion",
            "ubicación",
            "donde quedan",
            "dónde quedan",
            "como llego",
            "cómo llego",
        ]
    ):
        intent = "consulta_ubicacion"
        labels.append("consulta_ubicacion")

    if info_imagen:
        labels.append("incluye_imagen")

    return intent, labels


async def classify_intent(state: ChatbotState) -> ChatbotState:
    chat_input = state.get("chat_input")
    if not isinstance(chat_input, str) or not chat_input.strip():
        state["_node_metrics"] = {
            "provider": "heuristic",
            "model_id": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        return state

    info_imagen = state.get("info_imagen") if isinstance(state.get("info_imagen"), str) else None

    actions = _merge_actions(state)
    intent, labels = _heuristic_intent(chat_input, info_imagen)

    actions["intencion_detectada"] = intent
    actions["apply_labels"] = _merge_labels(actions, labels)
    state["actions"] = actions

    state["_node_metrics"] = {
        "provider": "heuristic",
        "model_id": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }
    return state


def _heuristic_lead(chat_input: str, intent: str | None) -> bool:
    t = (chat_input or "").lower()
    if intent in {"consulta_precio", "consulta_disponibilidad"}:
        return True
    if any(k in t for k in ["precio", "cuesta", "vale", "costo", "coste", "cuánto", "cuanto"]):
        return True
    if any(
        k in t
        for k in ["disponible", "disponibilidad", "hay", "tienen", "stock", "queda", "quedan"]
    ):
        return True
    return False


async def score_lead(state: ChatbotState) -> ChatbotState:
    chat_input = state.get("chat_input")
    if not isinstance(chat_input, str) or not chat_input.strip():
        state["_node_metrics"] = {
            "provider": "rules",
            "model_id": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        return state

    actions = _merge_actions(state)
    intent = actions.get("intencion_detectada")
    if not isinstance(intent, str):
        intent = None

    lead = _heuristic_lead(chat_input, intent)
    actions["lead_calificado"] = lead
    if lead:
        actions["apply_labels"] = _merge_labels(actions, ["lead_calificado"])
    state["actions"] = actions

    state["_node_metrics"] = {
        "provider": "rules",
        "model_id": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }
    return state


async def classify_intent_llm(state: ChatbotState) -> ChatbotState:
    chat_input = state.get("chat_input")
    if not isinstance(chat_input, str) or not chat_input.strip():
        return state

    info_imagen = state.get("info_imagen") if isinstance(state.get("info_imagen"), str) else None
    system = (
        "Clasifica el mensaje del usuario. Devuelve SOLO JSON con llaves: intent (string), labels (array de strings). "
        "Los labels deben ser cortos y en snake_case."
    )
    user = {
        "chat_input": chat_input,
        "info_imagen": info_imagen,
    }
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", escape_curly(system)),
            ("human", escape_curly(json.dumps(user, ensure_ascii=False))),
        ]
    )

    llm: Any
    provider = None
    model_id = None
    _api_key, _base_url = _get_db_credentials()
    # Leer classifier_model configurado en admin panel, con fallback a llm_model y luego al default
    _classifier_model = "openai/gpt-4.1-mini"
    try:
        from src.models.admin import admin_repo
        cfg = admin_repo.get_config("classifier_model") or admin_repo.get_config("llm_model")
        if cfg and cfg.value:
            _classifier_model = cfg.value
    except Exception:
        pass
    if _api_key:
        provider = "openai"
        model_id = _classifier_model
        llm = ChatOpenAI(
            model=model_id,
            api_key=SecretStr(_api_key),
            base_url=_base_url,
            temperature=0.0,
        )
    elif settings.google_api_key:
        provider = "google"
        model_id = "gemini-1.5-flash"
        llm = ChatGoogleGenerativeAI(
            model=model_id,
            api_key=SecretStr(settings.google_api_key),
            temperature=0.0,
        )
    else:
        return await classify_intent(state)

    try:
        response = await (prompt | llm).ainvoke({})
        content = response.content if isinstance(response.content, str) else str(response.content)
        parsed = json.loads(content)
        intent = parsed.get("intent")
        labels = parsed.get("labels")
        if not isinstance(intent, str) or not intent.strip():
            return await classify_intent(state)
        label_list: list[str] = []
        if isinstance(labels, list):
            label_list = [x for x in labels if isinstance(x, str)]
        actions = _merge_actions(state)
        actions["intencion_detectada"] = intent.strip()
        actions["apply_labels"] = _merge_labels(actions, label_list)
        state["actions"] = actions
        try:
            # Extraer métricas de uso de la respuesta
            usage = getattr(response, "usage_metadata", None)
            if not usage and hasattr(response, "response_metadata"):
                meta = response.response_metadata or {}
                usage = meta.get("token_usage") or meta.get("usage")

            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            if isinstance(usage, dict):
                input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
                output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
                total_tokens = usage.get("total_tokens") or (input_tokens + output_tokens)

            state["_node_metrics"] = {
                "provider": provider,
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": None,
            }
        except Exception as me:
            logger.warning("Error extrayendo métricas de NLU", error=str(me))
            state["_node_metrics"] = {
                "provider": provider,
                "model_id": model_id,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }
        return state
    except Exception as e:
        logger.warning("Fallo intent classifier LLM; usando heurística", error=str(e))
        return await classify_intent(state)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    if not s:
        return None
    if s.startswith("```"):
        parts = s.split("\n")
        if len(parts) >= 3:
            s = "\n".join(parts[1:-1]).strip()
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        s = s[start : end + 1]
    try:
        parsed = json.loads(s)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


async def score_lead_llm(state: ChatbotState) -> ChatbotState:
    chat_input = state.get("chat_input")
    if not isinstance(chat_input, str) or not chat_input.strip():
        return state

    actions = _merge_actions(state)
    intent = actions.get("intencion_detectada")
    intent_str = intent if isinstance(intent, str) and intent.strip() else None

    system = (
        "Determina si el mensaje del usuario indica intención comercial suficiente para considerarlo lead. "
        "Marca lead_calificado=true si pregunta por precio, disponibilidad/stock, compra, pedido, reservar, delivery o pagos. "
        "Devuelve SOLO JSON con llaves: lead_calificado (boolean), labels (array de strings). "
        "Los labels deben ser cortos y en snake_case."
    )
    user = {
        "chat_input": chat_input,
        "intent": intent_str,
        "info_imagen": state.get("info_imagen")
        if isinstance(state.get("info_imagen"), str)
        else None,
    }
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", escape_curly(system)),
            ("human", escape_curly(json.dumps(user, ensure_ascii=False))),
        ]
    )

    llm: Any
    provider = None
    model_id = None
    _api_key, _base_url = _get_db_credentials()
    _classifier_model = "openai/gpt-4.1-mini"
    try:
        from src.models.admin import admin_repo
        cfg = admin_repo.get_config("classifier_model") or admin_repo.get_config("llm_model")
        if cfg and cfg.value:
            _classifier_model = cfg.value
    except Exception:
        pass
    if _api_key:
        provider = "openai"
        model_id = _classifier_model
        llm = ChatOpenAI(
            model=model_id,
            api_key=SecretStr(_api_key),
            base_url=_base_url,
            temperature=0.0,
        )
    elif settings.google_api_key:
        provider = "google"
        model_id = "gemini-1.5-flash"
        llm = ChatGoogleGenerativeAI(
            model=model_id,
            api_key=SecretStr(settings.google_api_key),
            temperature=0.0,
        )
    else:
        return await score_lead(state)

    try:
        response = await (prompt | llm).ainvoke({})
        content = response.content if isinstance(response.content, str) else str(response.content)
        parsed = _extract_json_object(content)
        if not isinstance(parsed, dict):
            return await score_lead(state)

        raw_lead = parsed.get("lead_calificado")
        if not isinstance(raw_lead, bool):
            return await score_lead(state)
        lead = raw_lead

        labels = parsed.get("labels")
        label_list: list[str] = []
        if isinstance(labels, list):
            label_list = [x for x in labels if isinstance(x, str)]

        actions["lead_calificado"] = lead
        if lead:
            label_list = label_list + ["lead_calificado"]
        actions["apply_labels"] = _merge_labels(actions, label_list)
        state["actions"] = actions

        state["_node_metrics"] = {
            "provider": provider,
            "model_id": model_id,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        return state
    except Exception as e:
        logger.warning("Fallo lead scoring LLM; usando reglas", error=str(e))
        return await score_lead(state)
