"""
Event Emitter para broadcast de eventos del grafo.

Maneja conexiones WebSocket y broadcast de eventos de ejecución.
"""

import json
from datetime import datetime

from fastapi import WebSocket

from src.config.settings import settings
from src.events.models import ExecutionEvent, NodeEvent, NodeStatus
from src.utils.logger import get_logger
from src.utils.redis_client import redis_client

logger = get_logger(__name__)

_ORIGIN_ID = __import__("uuid").uuid4().hex


class EventEmitter:
    """
    Gestor de eventos para el dashboard.

    Mantiene conexiones WebSocket activas y emite eventos
    cuando el grafo se ejecuta.

    Ejemplo:
        # En un nodo del grafo
        await event_emitter.emit_node_start("generate_response", execution_id)

        # Al completar
        await event_emitter.emit_node_complete("generate_response", execution_id)
    """

    def __init__(self):
        self.connections: set[WebSocket] = set()
        self.executions: dict[str, ExecutionEvent] = {}
        self.execution_history: list[ExecutionEvent] = []
        self._max_history = 50
        self.logs_history: list[dict] = []
        self._max_logs_history = 500

    async def connect(self, websocket: WebSocket) -> None:
        """Agrega una conexión WebSocket (ya aceptada en el router)."""
        self.connections.add(websocket)
        logger.info(f"Dashboard conectado. Total: {len(self.connections)}")

        # Enviar estado inicial
        await self._send_initial_state(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remueve una conexión WebSocket."""
        self.connections.discard(websocket)
        logger.info(f"Dashboard desconectado. Total: {len(self.connections)}")

    async def _send_initial_state(self, websocket: WebSocket) -> None:
        """Envía el estado inicial al cliente."""
        from src.events.models import GraphDefinition

        try:
            # Enviar definición del grafo
            graph_def = GraphDefinition.from_chatbot_graph()
            await websocket.send_json(
                {
                    "type": "graph_definition",
                    "data": graph_def.model_dump(),
                }
            )

            # Enviar historial reciente
            await websocket.send_json(
                {
                    "type": "execution_history",
                    "data": [e.model_dump(mode="json") for e in self.execution_history[-10:]],
                }
            )

            # Enviar ejecución actual si existe
            if self.executions:
                for exec_event in self.executions.values():
                    await websocket.send_json(exec_event.to_broadcast())

        except Exception as e:
            logger.error(f"Error enviando estado inicial: {e}")

    async def broadcast(self, message: dict) -> None:
        """Envía mensaje a todas las conexiones."""
        if not self.connections:
            return

        disconnected = set()

        # Iterar sobre una copia para evitar 'Set changed size during iteration'
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)

        # Limpiar conexiones muertas fuera del loop
        if disconnected:
            self.connections -= disconnected

    async def emit(self, message: dict, publish: bool = True) -> None:
        await self.broadcast(message)
        if not publish:
            return
        try:
            m = message
            meta = None
            try:
                meta = m.get("meta") if isinstance(m, dict) else None
            except Exception:
                meta = None
            if not isinstance(meta, dict):
                meta = {}
            if "origin" not in meta:
                meta = {**meta, "origin": _ORIGIN_ID}
                m = {**message, "meta": meta}
            await redis_client.publish_json(settings.redis_events_channel, m)
        except Exception:
            return

    def ingest(self, message: dict) -> None:
        try:
            t = message.get("type")
            data = message.get("data")
            if t in {"execution_start", "execution_queued"} and isinstance(data, dict):
                try:
                    evt = ExecutionEvent.model_validate(data)
                except Exception:
                    return
                self.executions[evt.execution_id] = evt
                return
            if t == "execution_update" and isinstance(data, dict):
                eid = data.get("execution_id")
                if not eid or eid not in self.executions:
                    return
                cur_evt = self.executions[eid]
                merged = cur_evt.model_dump(mode="json")
                merged.update(data)
                try:
                    self.executions[eid] = ExecutionEvent.model_validate(merged)
                except Exception:
                    return
                return
            if t in {"node_start", "node_complete", "node_error"} and isinstance(data, dict):
                eid = data.get("execution_id")
                n = data.get("node")
                if not eid or not isinstance(n, dict):
                    return
                active_evt = self.executions.get(eid)
                if not active_evt:
                    return
                try:
                    node = NodeEvent.model_validate(n)
                except Exception:
                    return
                active_evt.nodes[node.node_name] = node
                if t == "node_start":
                    active_evt.current_node = node.node_name
                    active_evt.status = NodeStatus.RUNNING
                return
            if t == "node_skip" and isinstance(data, dict):
                eid = data.get("execution_id")
                node_name = data.get("node_name")
                if not eid or not node_name:
                    return
                active_evt = self.executions.get(eid)
                if not active_evt:
                    return
                active_evt.nodes[node_name] = NodeEvent(
                    node_name=node_name, status=NodeStatus.SKIPPED
                )
                return
            if t == "execution_complete" and isinstance(data, dict):
                eid = data.get("execution_id")
                if not eid:
                    return
                if eid in self.executions:
                    del self.executions[eid]
                try:
                    completed_evt = ExecutionEvent.model_validate(data)
                except Exception:
                    return
                self.execution_history.append(completed_evt)
                if len(self.execution_history) > self._max_history:
                    self.execution_history = self.execution_history[-self._max_history :]
                return
            if t == "log" and isinstance(data, dict):
                self.logs_history.append(data)
                if len(self.logs_history) > self._max_logs_history:
                    self.logs_history = self.logs_history[-self._max_logs_history :]
                eid = data.get("execution_id")
                if eid and eid in self.executions:
                    try:
                        self.executions[eid].logs.append(data)
                    except Exception:
                        pass
                return
        except Exception:
            return

    # === Métodos de Ejecución ===

    async def start_execution(
        self,
        execution_id: str,
        identifier: str = "",
        user_name: str = "",
        conversation_id: int = 0,
        chat_input: str = "",
    ) -> ExecutionEvent:
        """Inicia una nueva ejecución."""
        event = ExecutionEvent(
            execution_id=execution_id,
            identifier=identifier,
            user_name=user_name,
            conversation_id=conversation_id,
            chat_input=chat_input[:200],
            status=NodeStatus.RUNNING,
        )

        self.executions[execution_id] = event

        await self.emit(
            {
                "type": "execution_start",
                "data": event.model_dump(mode="json"),
            }
        )

        logger.debug(f"Ejecución iniciada: {execution_id}")
        try:
            log_item = {
                "timestamp": datetime.now().isoformat(),
                "execution_id": execution_id,
                "level": "info",
                "message": f"Inicio ejecución: {(identifier or user_name or execution_id[:8])} | '{chat_input}'",
                "node_name": None,
            }
            event.logs.append(log_item)
            self.logs_history.append(log_item)
            if len(self.logs_history) > self._max_logs_history:
                self.logs_history.pop(0)

            # Emitir log en tiempo real
            await self.emit({"type": "log", "data": log_item})
        except Exception:
            pass
        return event

    async def update_payload_in_preview(self, execution_id: str, preview: str) -> None:
        evt = self.executions.get(execution_id)
        if not evt:
            return
        try:
            evt.payload_in_preview = preview[:500]
        except Exception:
            evt.payload_in_preview = preview
        await self.emit(evt.to_broadcast())

    async def update_payload_out_preview(self, execution_id: str, preview: str) -> None:
        evt = self.executions.get(execution_id)
        if not evt:
            return
        try:
            evt.payload_out_preview = preview[:500]
        except Exception:
            evt.payload_out_preview = preview
        await self.emit(evt.to_broadcast())

    async def emit_node_start(self, node_name: str, execution_id: str) -> None:
        """Emite evento de inicio de nodo."""
        event = self.executions.get(execution_id)
        if not event:
            return

        node_event = NodeEvent(
            node_name=node_name,
            status=NodeStatus.RUNNING,
            started_at=datetime.now(),
        )

        event.nodes[node_name] = node_event
        event.current_node = node_name

        await self.emit(
            {
                "type": "node_start",
                "data": {
                    "execution_id": execution_id,
                    "node": node_event.model_dump(mode="json"),
                },
            }
        )
        try:
            log_item = {
                "timestamp": datetime.now().isoformat(),
                "execution_id": execution_id,
                "level": "running",
                "message": f"Inicio {node_name}",
                "node_name": node_name,
            }
            event.logs.append(log_item)
            self.logs_history.append(log_item)
            if len(self.logs_history) > self._max_logs_history:
                self.logs_history.pop(0)

            # Emitir log en tiempo real
            await self.emit({"type": "log", "data": log_item})
        except Exception:
            pass

    async def emit_node_complete(
        self,
        node_name: str,
        execution_id: str,
        output_preview: str | None = None,
        metrics: dict | None = None,
    ) -> None:
        """Emite evento de nodo completado."""
        event = self.executions.get(execution_id)
        if not event or node_name not in event.nodes:
            return

        node_event = event.nodes[node_name]
        node_event.status = NodeStatus.COMPLETED
        node_event.completed_at = datetime.now()

        if node_event.started_at:
            delta = node_event.completed_at - node_event.started_at
            node_event.duration_ms = delta.total_seconds() * 1000

        try:
            if (
                settings.alerts_enabled
                and node_event.duration_ms
                and node_event.duration_ms > settings.alert_max_duration_ms
            ):
                await self.emit(
                    {
                        "type": "alert",
                        "data": {
                            "execution_id": execution_id,
                            "node_name": node_name,
                            "reason": "duration_threshold",
                            "value": node_event.duration_ms,
                            "threshold": settings.alert_max_duration_ms,
                        },
                    }
                )
        except Exception:
            pass

        if output_preview:
            node_event.output_preview = output_preview[:100]

        if metrics:
            node_event.provider = metrics.get("provider")
            node_event.model_id = metrics.get("model_id")
            node_event.input_tokens = metrics.get("input_tokens")
            node_event.output_tokens = metrics.get("output_tokens")
            node_event.total_tokens = metrics.get("total_tokens")
            node_event.cost_usd = metrics.get("cost_usd")

            if node_event.cost_usd is None and node_event.model_id:
                try:
                    key = (
                        f"{node_event.provider}:{node_event.model_id}"
                        if node_event.provider
                        else node_event.model_id
                    )
                    inp_rate = (
                        settings.llm_pricing_input_per_1k_overrides.get(key)
                        or settings.llm_pricing_input_per_1k.get(node_event.model_id)
                        or 0.0
                    )
                    out_rate = (
                        settings.llm_pricing_output_per_1k_overrides.get(key)
                        or settings.llm_pricing_output_per_1k.get(node_event.model_id)
                        or 0.0
                    )
                    ci = (node_event.input_tokens or 0) / 1000.0 * inp_rate
                    co = (node_event.output_tokens or 0) / 1000.0 * out_rate
                    node_event.cost_usd = round(ci + co, 6)
                except Exception:
                    pass

            event.input_tokens_total = (event.input_tokens_total or 0) + (
                node_event.input_tokens or 0
            )
            event.output_tokens_total = (event.output_tokens_total or 0) + (
                node_event.output_tokens or 0
            )
            event.total_tokens_total = (event.total_tokens_total or 0) + (
                node_event.total_tokens or 0
            )
            event.cost_usd_total = (event.cost_usd_total or 0.0) + (node_event.cost_usd or 0.0)

            try:
                if settings.alerts_enabled:
                    if (
                        node_event.total_tokens
                        and node_event.total_tokens > settings.alert_max_total_tokens
                    ):
                        await self.emit(
                            {
                                "type": "alert",
                                "data": {
                                    "execution_id": execution_id,
                                    "node_name": node_name,
                                    "reason": "tokens_threshold",
                                    "value": node_event.total_tokens,
                                    "threshold": settings.alert_max_total_tokens,
                                },
                            }
                        )
            except Exception:
                pass

        await self.emit(
            {
                "type": "node_complete",
                "data": {
                    "execution_id": execution_id,
                    "node": node_event.model_dump(mode="json"),
                },
            }
        )
        try:
            log_item = {
                "timestamp": datetime.now().isoformat(),
                "execution_id": execution_id,
                "level": "success",
                "message": f"Fin {node_name} ({(node_event.duration_ms or 0):.0f}ms)",
                "node_name": node_name,
            }
            event.logs.append(log_item)
            self.logs_history.append(log_item)
            if len(self.logs_history) > self._max_logs_history:
                self.logs_history.pop(0)

            # Emitir log en tiempo real
            await self.emit({"type": "log", "data": log_item})
        except Exception:
            pass

    async def emit_node_error(
        self,
        node_name: str,
        execution_id: str,
        error: str,
    ) -> None:
        """Emite evento de error en nodo."""
        event = self.executions.get(execution_id)
        if not event:
            return

        if node_name not in event.nodes:
            event.nodes[node_name] = NodeEvent(
                node_name=node_name,
                status=NodeStatus.ERROR,
                started_at=datetime.now(),
            )

        node_event = event.nodes[node_name]
        node_event.status = NodeStatus.ERROR
        node_event.error = error[:200]
        node_event.completed_at = datetime.now()

        await self.emit(
            {
                "type": "node_error",
                "data": {
                    "execution_id": execution_id,
                    "node": node_event.model_dump(mode="json"),
                },
            }
        )
        try:
            log_item = {
                "timestamp": datetime.now().isoformat(),
                "execution_id": execution_id,
                "level": "error",
                "message": error,
                "node_name": node_name,
            }
            event.logs.append(log_item)
            self.logs_history.append(log_item)
            if len(self.logs_history) > self._max_logs_history:
                self.logs_history.pop(0)

            # Emitir log en tiempo real
            await self.emit({"type": "log", "data": log_item})
        except Exception:
            pass

    async def emit_node_skip(self, node_name: str, execution_id: str) -> None:
        """Emite evento de nodo saltado."""
        event = self.executions.get(execution_id)
        if not event:
            return

        event.nodes[node_name] = NodeEvent(
            node_name=node_name,
            status=NodeStatus.SKIPPED,
        )

        await self.emit(
            {
                "type": "node_skip",
                "data": {
                    "execution_id": execution_id,
                    "node_name": node_name,
                },
            }
        )

    async def complete_execution(
        self,
        execution_id: str,
        ai_response: str | None = None,
        error: str | None = None,
    ) -> None:
        """Completa una ejecución."""
        event = self.executions.get(execution_id)
        if not event:
            return

        event.completed_at = datetime.now()
        event.status = NodeStatus.ERROR if error else NodeStatus.COMPLETED
        event.ai_response = ai_response[:500] if ai_response else None
        event.error = error
        event.current_node = None

        # Log final de ejecución
        try:
            tokens_total = event.total_tokens_total or (
                (event.input_tokens_total or 0) + (event.output_tokens_total or 0)
            )
            started = event.started_at
            completed = event.completed_at
            duration_ms = None
            try:
                if started and completed:
                    duration_ms = (completed - started).total_seconds() * 1000
            except Exception:
                duration_ms = None

            path = []
            try:
                for name, n in event.nodes.items():
                    path.append(name)
            except Exception:
                path = []
            path_str = " → ".join(path) if path else ""

            final_log = {
                "timestamp": datetime.now().isoformat(),
                "execution_id": execution_id,
                "level": ("error" if error else "success"),
                "message": (
                    f"Ejecución fallida: {error}"
                    if error
                    else f"Ejecución completada | tok:{tokens_total} cost:{(event.cost_usd_total or 0.0):.6f} dur:{(duration_ms or 0):.0f}ms"
                ),
                "node_name": None,
            }
            event.logs.append(final_log)
            if path_str:
                route_log = {
                    "timestamp": datetime.now().isoformat(),
                    "execution_id": execution_id,
                    "level": "info",
                    "message": f"Ruta: {path_str}",
                    "node_name": None,
                }
                event.logs.append(route_log)
                self.logs_history.append(route_log)
                # Emitir ruta
                await self.emit({"type": "log", "data": route_log})

            self.logs_history.append(final_log)
            if len(self.logs_history) > self._max_logs_history:
                self.logs_history.pop(0)

            # Emitir log final
            await self.emit({"type": "log", "data": final_log})
        except Exception:
            pass

        # Guardar en historial
        self.execution_history.append(event)
        if len(self.execution_history) > self._max_history:
            self.execution_history.pop(0)

        # Limpiar ejecución activa
        del self.executions[execution_id]

        try:
            data = event.model_dump(mode="json")
            await redis_client.push_to_list(
                "metrics:executions", json.dumps(data), ttl=settings.metrics_ttl_seconds
            )
            try:
                await redis_client.set_with_ttl(
                    f"metrics:execution:{execution_id}",
                    json.dumps(data),
                    ttl=settings.metrics_ttl_seconds,
                )
            except Exception:
                await redis_client.set_value(f"metrics:execution:{execution_id}", json.dumps(data))
            try:
                await redis_client.set_with_ttl(
                    f"metrics:logs:{execution_id}",
                    json.dumps(event.logs),
                    ttl=settings.metrics_ttl_seconds,
                )
            except Exception:
                await redis_client.set_value(f"metrics:logs:{execution_id}", json.dumps(event.logs))
        except Exception:
            pass

        await self.emit(
            {
                "type": "execution_complete",
                "data": event.model_dump(mode="json"),
            }
        )

        logger.debug(f"Ejecución completada: {execution_id}")

    async def emit_log(
        self,
        execution_id: str,
        level: str,
        message: str,
        node_name: str | None = None,
    ) -> None:
        """Emite un log."""
        log_item = {
            "timestamp": datetime.now().isoformat(),
            "execution_id": execution_id,
            "level": level,
            "message": message,
            "node_name": node_name,
        }
        try:
            evt = self.executions.get(execution_id)
            if evt:
                evt.logs.append(log_item)
            self.logs_history.append(log_item)
            if len(self.logs_history) > self._max_logs_history:
                self.logs_history.pop(0)
        except Exception:
            pass
        await self.emit(
            {
                "type": "log",
                "data": log_item,
            }
        )


# Instancia global
event_emitter = EventEmitter()
