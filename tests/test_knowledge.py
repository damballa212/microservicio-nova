import pytest

from src.models.state import create_initial_state
from src.nodes.knowledge import (
    _find_best_inventory_matches,
    _rows_from_sheet_values,
    plan_knowledge,
)


@pytest.mark.asyncio
async def test_plan_knowledge_uses_sheets_when_inventory_query_and_sheet_id_present():
    state = create_initial_state({"body": {"event": "message_created"}})
    state["chat_input"] = "Tienen pizza hawaiana disponible?"
    state["inventory_query"] = "pizza hawaiana"
    state["google_sheet_id"] = "1abc"
    state["actions"] = {"intencion_detectada": "consulta_disponibilidad"}

    out = await plan_knowledge(state)
    plan = out.get("knowledge_plan")
    assert isinstance(plan, dict)
    assert plan.get("use_sheets") is True
    assert plan.get("use_docs") is True


@pytest.mark.asyncio
async def test_plan_knowledge_disables_docs_for_saludo():
    state = create_initial_state({"body": {"event": "message_created"}})
    state["chat_input"] = "Hola"
    state["actions"] = {"intencion_detectada": "saludo"}

    out = await plan_knowledge(state)
    plan = out.get("knowledge_plan")
    assert isinstance(plan, dict)
    assert plan.get("use_docs") is False


def test_rows_from_sheet_values_maps_producto_stock_disponible():
    values = [
        ["Producto", "Stock", "Disponible"],
        ["Pizza Hawaiana", "5", "Sí"],
        ["Pizza Margarita", "0", "No"],
    ]
    rows = _rows_from_sheet_values(values)
    assert len(rows) == 2
    assert rows[0]["producto"] == "Pizza Hawaiana"
    assert rows[0]["stock"] == "5"
    assert rows[0]["disponible"] == "Sí"


def test_find_best_inventory_matches_returns_best_row():
    inventory_rows = [
        {"producto": "Pizza Hawaiana", "stock": "5", "disponible": "Sí"},
        {"producto": "Pizza Margarita", "stock": "3", "disponible": "Sí"},
    ]
    matches = _find_best_inventory_matches(inventory_rows, "hawaiana", top_k=1)
    assert len(matches) == 1
    row = matches[0].get("row")
    assert isinstance(row, dict)
    assert row.get("producto") == "Pizza Hawaiana"
