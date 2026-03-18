"""
Router para endpoints de métricas.

Endpoints para visualización de métricas:
- Historial de ejecuciones
- Logs
- Resumen de métricas
- Tendencias
"""

import json

from fastapi import APIRouter

from src.config.settings import settings
from src.events.emitter import event_emitter
from src.utils.logger import get_logger
from src.utils.redis_client import redis_client

logger = get_logger(__name__)

metrics_router = APIRouter(prefix="/metrics", tags=["Metrics"])


@metrics_router.get("/summary")
async def metrics_summary():
    """Resumen de métricas de ejecuciones."""
    try:
        raw = await redis_client.get_list("metrics:executions")
        executions = []
        for r in raw:
            try:
                executions.append(json.loads(r))
            except Exception:
                pass

        total = len(executions)
        if total == 0:
            return {
                "total_executions": 0,
                "success_rate": None,
                "avg_duration_ms": None,
                "avg_tokens": None,
                "total_cost_usd": 0.0,
                "nodes": {},
            }

        success_count = sum(1 for e in executions if e.get("status") == "completed")
        
        durations = []
        tokens_list = []
        total_cost = 0.0
        nodes_stats: dict[str, dict] = {}
        
        for e in executions:
            # Duración
            try:
                s = e.get("started_at")
                c = e.get("completed_at")
                if s and c:
                    from datetime import datetime
                    st = datetime.fromisoformat(s.replace("Z", "+00:00"))
                    ct = datetime.fromisoformat(c.replace("Z", "+00:00"))
                    durations.append((ct - st).total_seconds() * 1000)
            except Exception:
                pass
            
            # Tokens
            tok = e.get("total_tokens_total")
            if isinstance(tok, (int, float)):
                tokens_list.append(tok)
            
            # Costo
            cost = e.get("cost_usd_total")
            if isinstance(cost, (int, float)):
                total_cost += cost
            
            # Nodos
            nodes = e.get("nodes", {})
            for name, nd in nodes.items():
                if name not in nodes_stats:
                    nodes_stats[name] = {"count": 0, "errors": 0, "total_ms": 0.0}
                nodes_stats[name]["count"] += 1
                if nd.get("status") == "error":
                    nodes_stats[name]["errors"] += 1
                dm = nd.get("duration_ms")
                if isinstance(dm, (int, float)):
                    nodes_stats[name]["total_ms"] += dm

        return {
            "total_executions": total,
            "success_rate": round(success_count / total * 100, 2) if total else None,
            "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else None,
            "avg_tokens": round(sum(tokens_list) / len(tokens_list), 2) if tokens_list else None,
            "total_cost_usd": round(total_cost, 4),
            "nodes": {
                name: {
                    "count": s["count"],
                    "error_rate": round(s["errors"] / s["count"] * 100, 2) if s["count"] else 0,
                    "avg_ms": round(s["total_ms"] / s["count"], 2) if s["count"] else 0,
                }
                for name, s in nodes_stats.items()
            },
        }
    except Exception as e:
        logger.error("Error en metrics_summary", error=str(e))
        return {"error": str(e)}


@metrics_router.get("/execution/{execution_id}")
async def metrics_execution(execution_id: str):
    """Métricas detalladas de una ejecución específica."""
    try:
        raw = await redis_client.get_value(f"metrics:execution:{execution_id}")
        if raw:
            return json.loads(raw)
        return {"error": "Execution not found"}
    except Exception as e:
        return {"error": str(e)}


@metrics_router.get("/node/{node_name}")
async def metrics_node(node_name: str):
    """Métricas agregadas de un nodo específico."""
    try:
        raw = await redis_client.get_list("metrics:executions")
        node_data: list[dict] = []
        
        for r in raw:
            try:
                ex = json.loads(r)
                nodes = ex.get("nodes", {})
                if node_name in nodes:
                    nd = nodes[node_name]
                    node_data.append({
                        "execution_id": ex.get("execution_id"),
                        "status": nd.get("status"),
                        "duration_ms": nd.get("duration_ms"),
                        "tokens": nd.get("total_tokens"),
                        "cost_usd": nd.get("cost_usd"),
                    })
            except Exception:
                pass

        return {
            "node_name": node_name,
            "total_calls": len(node_data),
            "executions": node_data[-20:],  # Últimas 20
        }
    except Exception as e:
        return {"error": str(e)}


@metrics_router.get("/trends")
async def metrics_trends():
    """Tendencias de métricas en el tiempo."""
    try:
        raw = await redis_client.get_list("metrics:executions")
        
        # Agrupar por hora
        hourly: dict[str, dict] = {}
        for r in raw:
            try:
                ex = json.loads(r)
                ts = ex.get("started_at", "")
                if ts:
                    hour = ts[:13]  # YYYY-MM-DDTHH
                    if hour not in hourly:
                        hourly[hour] = {"count": 0, "tokens": 0, "cost": 0.0}
                    hourly[hour]["count"] += 1
                    hourly[hour]["tokens"] += ex.get("total_tokens_total") or 0
                    hourly[hour]["cost"] += ex.get("cost_usd_total") or 0.0
            except Exception:
                pass

        return {
            "hourly": [
                {"hour": h, "executions": d["count"], "tokens": d["tokens"], "cost": round(d["cost"], 4)}
                for h, d in sorted(hourly.items())[-24:]  # Últimas 24 horas
            ]
        }
    except Exception as e:
        return {"error": str(e)}


@metrics_router.post("/reset")
async def metrics_reset():
    """Limpia todas las métricas."""
    try:
        await redis_client.delete_key("metrics:executions")
        return {"status": "ok", "message": "Metrics reset"}
    except Exception as e:
        return {"error": str(e)}


# === LOGS ===

@metrics_router.get("/logs")
async def logs_history():
    """Historial de logs."""
    return {"logs": event_emitter.logs_history[-100:]}


@metrics_router.get("/logs/{execution_id}")
async def logs_execution(execution_id: str):
    """Logs de una ejecución específica."""
    try:
        raw = await redis_client.get_value(f"metrics:logs:{execution_id}")
        if raw:
            return {"logs": json.loads(raw)}
        
        # Fallback a memoria
        evt = event_emitter.executions.get(execution_id)
        if evt:
            return {"logs": evt.logs}
        
        return {"logs": []}
    except Exception as e:
        return {"error": str(e)}


# === HISTORIAL ===

@metrics_router.get("/executions")
async def execution_history():
    """Historial de ejecuciones recientes."""
    from src.events.models import ExecutionEvent

    active = [e.model_dump(mode="json") for e in event_emitter.executions.values()]
    recent = [e.model_dump(mode="json") for e in event_emitter.execution_history[-20:]]
    
    # Cargar de Redis si no hay suficientes
    if len(recent) < 20:
        try:
            raw = await redis_client.get_list("metrics:executions")
            for r in raw[-20:]:
                try:
                    recent.append(json.loads(r))
                except Exception:
                    pass
        except Exception:
            pass

    return {
        "active": active,
        "recent": recent[-20:],
    }
