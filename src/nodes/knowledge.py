import json
import os
import re
from typing import Any

from src.config.settings import settings
from src.models.state import ChatbotState
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _merge_actions(state: ChatbotState) -> dict[str, Any]:
    current = state.get("actions")
    return dict(current) if isinstance(current, dict) else {}


def _normalize_text(value: str) -> str:
    s = (value or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize(value: str) -> list[str]:
    s = _normalize_text(value)
    if not s:
        return []
    tokens = [t for t in s.split(" ") if len(t) > 2]
    stop = {
        "tienen",
        "tiene",
        "hay",
        "queda",
        "quedan",
        "disponible",
        "disponibilidad",
        "stock",
        "inventario",
        "precio",
        "cuanto",
        "cuánto",
        "vale",
        "cuesta",
        "por",
        "para",
        "con",
        "sin",
        "una",
        "uno",
        "unos",
        "unas",
        "el",
        "la",
        "los",
        "las",
        "de",
        "del",
        "al",
        "me",
        "mi",
        "tu",
        "su",
        "porfavor",
        "porfa",
        "favor",
        "quiero",
        "deseo",
    }
    return [t for t in tokens if t not in stop]


def _score_match(query: str, product: str) -> float:
    q_tokens = set(_tokenize(query))
    p_tokens = set(_tokenize(product))
    if not q_tokens or not p_tokens:
        qn = _normalize_text(query)
        pn = _normalize_text(product)
        if not qn or not pn:
            return 0.0
        if qn in pn or pn in qn:
            return 0.6
        return 0.0
    overlap = len(q_tokens & p_tokens)
    if overlap == 0:
        qn = _normalize_text(query)
        pn = _normalize_text(product)
        if qn and pn and (qn in pn or pn in qn):
            return 0.55
        return 0.0
    return overlap / max(len(p_tokens), 1)


def _find_best_inventory_matches(
    inventory_rows: list[dict[str, str]], query: str, top_k: int = 3
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, str]]] = []
    for row in inventory_rows:
        prod = row.get("producto") or row.get("product") or row.get("name") or ""
        sc = _score_match(query, prod)
        if sc > 0:
            scored.append((sc, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    for sc, row in scored[: max(top_k, 1)]:
        out.append({"score": sc, "row": row})
    return out


def _rows_from_sheet_values(values: list[list[Any]]) -> list[dict[str, str]]:
    if not values or not isinstance(values, list):
        return []
    header_raw = values[0] if isinstance(values[0], list) else []
    headers = [str(h or "").strip() for h in header_raw]
    norm_headers = [_normalize_text(h) for h in headers]
    idx_producto = None
    idx_stock = None
    idx_disponible = None
    for i, nh in enumerate(norm_headers):
        if idx_producto is None and nh in {"producto", "product", "nombre", "name"}:
            idx_producto = i
        if idx_stock is None and nh in {"stock", "cantidad", "qty", "cantidad_disponible"}:
            idx_stock = i
        if idx_disponible is None and nh in {"disponible", "available", "activo"}:
            idx_disponible = i
    if idx_producto is None:
        return []
    rows: list[dict[str, str]] = []
    for r in values[1:]:
        if not isinstance(r, list):
            continue
        prod = str(r[idx_producto] if idx_producto < len(r) else "").strip()
        if not prod:
            continue
        stock = ""
        disp = ""
        if idx_stock is not None:
            stock = str(r[idx_stock] if idx_stock < len(r) else "").strip()
        if idx_disponible is not None:
            disp = str(r[idx_disponible] if idx_disponible < len(r) else "").strip()
        row = {"producto": prod}
        if stock:
            row["stock"] = stock
        if disp:
            row["disponible"] = disp
        rows.append(row)
    return rows


def _summarize_inventory_matches(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "No se encontraron coincidencias de inventario para la consulta."
    lines: list[str] = []
    for m in matches[:3]:
        row = m.get("row") if isinstance(m, dict) else None
        if not isinstance(row, dict):
            continue
        prod = str(row.get("producto") or "").strip()
        if not prod:
            continue
        stock = str(row.get("stock") or "").strip()
        disp = str(row.get("disponible") or "").strip()
        parts = [f"Producto: {prod}"]
        if disp:
            parts.append(f"Disponible: {disp}")
        if stock:
            parts.append(f"Stock: {stock}")
        lines.append(" | ".join(parts))
    return (
        "\n".join(lines)
        if lines
        else "No se encontraron coincidencias de inventario para la consulta."
    )


async def plan_knowledge(state: ChatbotState) -> ChatbotState:
    actions = _merge_actions(state)
    intent = actions.get("intencion_detectada")
    intent_str = intent.strip() if isinstance(intent, str) else ""
    chat_input = state.get("chat_input")
    query = chat_input if isinstance(chat_input, str) else ""
    inventory_query = (
        state.get("inventory_query") if isinstance(state.get("inventory_query"), str) else None
    )
    google_sheet_id = (
        state.get("google_sheet_id") if isinstance(state.get("google_sheet_id"), str) else ""
    )

    use_sheets = bool(inventory_query and google_sheet_id)
    use_docs = True
    if intent_str in {"saludo"}:
        use_docs = False

    plan = {
        "intent": intent_str or None,
        "use_sheets": use_sheets,
        "use_docs": use_docs,
        "docs_query": query,
        "inventory_query": inventory_query,
        "tenant": state.get("tenant_slug") or state.get("tenant_id") or "",
    }
    state["knowledge_plan"] = plan
    return state


async def lookup_inventory_sheets(state: ChatbotState) -> ChatbotState:
    raw_plan = state.get("knowledge_plan")
    plan = raw_plan if isinstance(raw_plan, dict) else {}
    if not bool(plan.get("use_sheets")):
        return state
    sheet_id = state.get("google_sheet_id") if isinstance(state.get("google_sheet_id"), str) else ""
    inv_query = (
        state.get("inventory_query") if isinstance(state.get("inventory_query"), str) else ""
    )
    if not sheet_id or not inv_query:
        return state

    path = os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON") or getattr(
        settings, "google_sheets_service_account_json", ""
    )
    if not isinstance(path, str) or not path:
        state["sheets_result"] = {
            "text": "Inventario no disponible (credenciales no configuradas).",
            "error": "missing_credentials",
        }
        return state

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception:
        state["sheets_result"] = {
            "text": "Inventario no disponible (dependencias de Google no instaladas).",
            "error": "missing_google_deps",
        }
        return state

    try:
        credentials = service_account.Credentials.from_service_account_file(
            path,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = meta.get("sheets") or []
        title = None
        if isinstance(sheets, list) and sheets:
            props = sheets[0].get("properties") if isinstance(sheets[0], dict) else None
            if isinstance(props, dict):
                title = props.get("title")
        sheet_name = str(title) if isinstance(title, str) and title else "Sheet1"
        value_range = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=f"{sheet_name}!A:Z",
            )
            .execute()
        )
        values = value_range.get("values") or []
        rows = _rows_from_sheet_values(values if isinstance(values, list) else [])
        matches = _find_best_inventory_matches(rows, inv_query, top_k=3)
        summary = _summarize_inventory_matches(matches)
        state["sheets_result"] = {
            "text": summary,
            "matches": [m.get("row") for m in matches if isinstance(m, dict)],
        }
        return state
    except Exception as e:
        import traceback
        error_msg = str(e)
        logger.error(
            "Error crítico en lookup_inventory_sheets",
            error=error_msg,
            sheet_id=sheet_id,
            traceback=traceback.format_exc(),
        )
        state["sheets_result"] = {
            "text": "Lo siento, hubo un error técnico al consultar el inventario.",
            "error": error_msg[:200],
        }
        return state


def _flowify_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    api_key = os.getenv("FLOWIFY_API_KEY") or getattr(settings, "flowify_api_key", "")
    if isinstance(api_key, str) and api_key:
        headers["X-API-Key"] = api_key
    token = os.getenv("FLOWIFY_API_TOKEN") or getattr(settings, "flowify_api_token", "")
    if isinstance(token, str) and token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_rag_docs(data: Any) -> list[dict[str, str]]:
    """Parse RAG document results with improved flexibility and metadata extraction."""
    docs: list[dict[str, str]] = []
    if isinstance(data, dict):
        candidates = data.get("docs")
        if candidates is None:
            candidates = data.get("results")
        if candidates is None:
            candidates = data.get("data")
        if candidates is None:
            candidates = data.get("documents")
    else:
        candidates = data

    if isinstance(candidates, list):
        for it in candidates[:5]:  # Incrementado de 3 a 5 para más contexto
            if not isinstance(it, dict):
                continue
            # Intentar extraer título de múltiples campos posibles
            title = (
                it.get("title")
                or it.get("titulo")
                or it.get("name")
                or it.get("nombre")
                or it.get("heading")
                or ""
            )
            # Intentar extraer contenido de múltiples campos posibles
            content = (
                it.get("content")
                or it.get("contenido")
                or it.get("text")
                or it.get("body")
                or it.get("description")
                or ""
            )

            # Extraer metadata adicional si está disponible
            source = it.get("source") or it.get("doc_id") or ""

            if isinstance(content, str) and content.strip():
                doc = {
                    "title": str(title or "Documento sin título"),
                    "content": content[:3000],  # Incrementado de 2000 a 3000 para más contexto
                }
                if source:
                    doc["source"] = str(source)[:200]
                docs.append(doc)
    return docs


async def retrieve_docs_rag(state: ChatbotState) -> ChatbotState:
    raw_plan = state.get("knowledge_plan")
    plan = raw_plan if isinstance(raw_plan, dict) else {}
    if not bool(plan.get("use_docs")):
        return state
    tenant_id = state.get("tenant_id") or ""
    query = plan.get("docs_query") or ""
    if not isinstance(query, str) or not query.strip():
        return state
    try:
        from src.rag.vector_store import reranked_search

        results = await reranked_search(str(tenant_id), query, 5)  # Incrementado de 3 a 5
        docs = _parse_rag_docs({"docs": results})
        if docs:
            state["rag_docs"] = docs
            logger.info(
                "Documentos RAG recuperados exitosamente",
                tenant_id=tenant_id,
                query_length=len(query),
                docs_found=len(docs),
            )
        else:
            logger.debug(
                "No se encontraron documentos RAG relevantes",
                tenant_id=tenant_id,
                query=query[:100],
            )
        return state
    except Exception as e:
        import traceback
        logger.error(
            "Error crítico en retrieval RAG",
            error=str(e),
            tenant_id=tenant_id,
            query=query[:100],
            traceback=traceback.format_exc(),
        )
        return state


async def merge_knowledge(state: ChatbotState) -> ChatbotState:
    docs = state.get("rag_docs")
    if isinstance(docs, list):
        normalized_docs: list[dict[str, str]] = []
        for d in docs[:3]:
            if not isinstance(d, dict):
                continue
            t = d.get("title")
            c = d.get("content")
            if isinstance(c, str) and c.strip():
                normalized_docs.append({"title": str(t or ""), "content": c[:2000]})
        state["rag_docs"] = normalized_docs
    else:
        state["rag_docs"] = []

    sr = state.get("sheets_result")
    if sr is None:
        return state
    if not isinstance(sr, dict):
        state["sheets_result"] = None
        return state
    text = sr.get("text")
    if not isinstance(text, str):
        state["sheets_result"] = None
        return state
    state["sheets_result"] = {k: v for k, v in sr.items() if k in {"text", "matches", "error"}}
    return state


def serialize_knowledge_plan(state: ChatbotState) -> str:
    raw_plan = state.get("knowledge_plan")
    plan = raw_plan if isinstance(raw_plan, dict) else {}
    try:
        return json.dumps(plan, ensure_ascii=False)
    except Exception:
        return str(plan)
