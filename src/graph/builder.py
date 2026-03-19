"""
Constructor del grafo LangGraph con emisión de eventos.

Define el flujo completo del chatbot como un StateGraph.
Emite eventos para visualización en tiempo real en el dashboard.
"""

import asyncio
import json
import os
import socket
import time
import uuid
from typing import Any, cast

from langgraph.graph import END, StateGraph

from src.config.settings import settings
from src.events.emitter import event_emitter
from src.events.models import ExecutionEvent, NodeStatus
from src.models.state import ChatbotState, create_initial_state
from src.nodes.ai_agent import generate_response
from src.nodes.buffer import (
    add_to_buffer,
    check_buffer_status,
    route_buffer_decision,
    wait_for_messages,
)
from src.nodes.escalation import (
    classify_escalation,
    escalate_to_human,
    route_escalation,
)
from src.nodes.formatter import format_response

# Conocimiento (RAG/Sheets) ahora se invoca bajo demanda por el LLM vía herramientas
from src.nodes.multimodal import process_multimodal
from src.nodes.nlu import classify_intent, score_lead  # heurísticas; el agente principal maneja intent/lead via JSON
from src.nodes.outbound_webhook import post_to_outbound_webhook
from src.nodes.validation import (
    check_bot_state,
    extract_message_data,
    route_after_bot_check,
    route_after_event_validation,
    route_after_sender_validation,
    validate_event,
    validate_sender,
)
from src.utils.logger import get_logger
from src.utils.redis_client import redis_client

logger = get_logger(__name__)


def wrap_node_with_events(node_func: Any, node_name: str):
    """
    Wrapper que emite eventos al ejecutar un nodo.

    Args:
        node_func: Función del nodo original
        node_name: Nombre del nodo

    Returns:
        Función envuelta que emite eventos
    """
    import asyncio

    if asyncio.iscoroutinefunction(node_func):

        async def async_wrapper(state: ChatbotState) -> ChatbotState:
            execution_id = str(state.get("_execution_id") or "")
            if not execution_id:
                try:
                    # Fallback: usar la ejecución activa más reciente
                    if event_emitter.executions:
                        execution_id = str(next(iter(event_emitter.executions.keys())))
                        state["_execution_id"] = execution_id
                except Exception:
                    execution_id = ""

            await event_emitter.emit_node_start(node_name, execution_id)

            try:
                result = await node_func(state)
                result_state = cast(ChatbotState, result) if isinstance(result, dict) else state

                # Obtener preview del output
                output_preview = None
                if node_name == "generate_response":
                    output_preview = str(result_state.get("ai_response", ""))[:100]
                elif node_name == "extract_data":
                    output_preview = f"User: {result_state.get('user_name', 'N/A')}"
                elif node_name == "post_to_outbound_webhook":
                    try:
                        resp = (
                            result_state.get("_outbound_response", {})
                            if isinstance(result_state, dict)
                            else {}
                        )
                        sc = resp.get("status_code")
                        output_preview = f"status:{sc}" if sc is not None else None
                    except Exception:
                        output_preview = None

                metrics = None
                try:
                    metrics = (
                        result_state.get("_node_metrics")
                        if isinstance(result_state, dict)
                        else None
                    )
                    if isinstance(result_state, dict) and "_node_metrics" in result_state:
                        del result_state["_node_metrics"]
                except Exception:
                    metrics = None
                await event_emitter.emit_node_complete(
                    node_name, execution_id, output_preview, metrics
                )
                return result_state

            except Exception as e:
                await event_emitter.emit_node_error(node_name, execution_id, str(e))
                raise

        return async_wrapper
    else:

        def sync_wrapper(state: ChatbotState) -> ChatbotState:
            execution_id = str(state.get("_execution_id") or "")

            # Para funciones sync, usamos asyncio.create_task si hay event loop
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(event_emitter.emit_node_start(node_name, execution_id))
            except RuntimeError:
                pass

            try:
                result = node_func(state)
                result_state = cast(ChatbotState, result) if isinstance(result, dict) else state

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(event_emitter.emit_node_complete(node_name, execution_id))
                except RuntimeError:
                    pass

                return result_state

            except Exception as e:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(event_emitter.emit_node_error(node_name, execution_id, str(e)))
                except RuntimeError:
                    pass
                raise

        return sync_wrapper


def build_chatbot_graph() -> Any:
    """
    Construye el grafo completo del chatbot con emisión de eventos.
    """
    logger.info("Construyendo grafo del chatbot")

    graph = StateGraph(ChatbotState)

    # === AGREGAR NODOS CON EVENTOS ===

    # Fase 1: Validaciones
    graph.add_node("validate_event", wrap_node_with_events(validate_event, "validate_event"))
    graph.add_node("validate_sender", wrap_node_with_events(validate_sender, "validate_sender"))
    graph.add_node("check_bot_state", wrap_node_with_events(check_bot_state, "check_bot_state"))
    graph.add_node("extract_data", wrap_node_with_events(extract_message_data, "extract_data"))

    # Fase 2: Buffer
    graph.add_node("add_to_buffer", wrap_node_with_events(add_to_buffer, "add_to_buffer"))
    graph.add_node(
        "check_buffer_status", wrap_node_with_events(check_buffer_status, "check_buffer_status")
    )
    graph.add_node(
        "wait_for_messages", wrap_node_with_events(wait_for_messages, "wait_for_messages")
    )

    # Fase 3: Procesamiento
    graph.add_node(
        "process_multimodal", wrap_node_with_events(process_multimodal, "process_multimodal")
    )

    # classify_intent: heurística rápida (sin LLM). El veredicto final de intent/lead
    # viene dentro del JSON que retorna generate_response (campos nlu + actions).
    graph.add_node("classify_intent", wrap_node_with_events(classify_intent, "classify_intent"))

    # score_lead: reglas simples (sin LLM). El agente principal lo confirma en su JSON.
    graph.add_node("score_lead", wrap_node_with_events(score_lead, "score_lead"))

    # Fase 4: IA
    graph.add_node(
        "generate_response", wrap_node_with_events(generate_response, "generate_response")
    )
    graph.add_node("format_response", wrap_node_with_events(format_response, "format_response"))

    graph.add_node(
        "post_to_outbound_webhook",
        wrap_node_with_events(post_to_outbound_webhook, "post_to_outbound_webhook"),
    )

    # Fase 6: Escalamiento
    graph.add_node(
        "classify_escalation", wrap_node_with_events(classify_escalation, "classify_escalation")
    )
    graph.add_node(
        "escalate_to_human", wrap_node_with_events(escalate_to_human, "escalate_to_human")
    )

    # === CONFIGURAR EDGES ===

    graph.set_entry_point("validate_event")

    graph.add_conditional_edges(
        "validate_event", route_after_event_validation, {"continue": "validate_sender", "stop": END}
    )

    graph.add_conditional_edges(
        "validate_sender",
        route_after_sender_validation,
        {"continue": "check_bot_state", "stop": END},
    )

    graph.add_conditional_edges(
        "check_bot_state",
        route_after_bot_check,
        {
            "continue": "extract_data",
            "escalate": "escalate_to_human",
            "stop": "post_to_outbound_webhook",
        },
    )

    graph.add_edge("extract_data", "add_to_buffer")
    graph.add_edge("add_to_buffer", "check_buffer_status")

    graph.add_conditional_edges(
        "check_buffer_status",
        route_buffer_decision,
        {"wait": "wait_for_messages", "process": "process_multimodal", "duplicate": END},
    )

    graph.add_edge("wait_for_messages", "check_buffer_status")
    graph.add_edge("process_multimodal", "classify_intent")
    # Ir directo a scoring de lead sin conocimiento previo; el LLM pedirá herramientas si hace falta
    graph.add_edge("classify_intent", "score_lead")
    graph.add_edge("score_lead", "generate_response")
    graph.add_edge("generate_response", "format_response")
    graph.add_edge("format_response", "classify_escalation")

    graph.add_conditional_edges(
        "classify_escalation",
        route_escalation,
        {"escalate": "escalate_to_human", "continue": "post_to_outbound_webhook"},
    )

    graph.add_edge("escalate_to_human", "post_to_outbound_webhook")
    graph.add_edge("post_to_outbound_webhook", END)

    logger.info("Grafo del chatbot construido exitosamente")

    return graph.compile()


# Grafo compilado global
chatbot_graph: Any = build_chatbot_graph()

_worker_tasks: list[asyncio.Task] = []
_worker_stop: asyncio.Event | None = None
_consumer_base: str | None = None


async def run_chatbot(payload: dict, execution_id: str | None = None) -> dict:
    """
    Ejecuta el chatbot con un payload de webhook.
    Emite eventos para el dashboard en tiempo real.
    """
    execution_id = execution_id or str(uuid.uuid4())
    logger.info("Ejecutando grafo del chatbot", execution_id=execution_id)

    # Crear estado inicial con execution_id
    initial_state = create_initial_state(payload)
    initial_state["_execution_id"] = execution_id

    # Extraer info básica del payload para el evento
    body = payload.get("body", payload)
    conversation = body.get("conversation", {})
    messages = conversation.get("messages", [{}])
    message = messages[0] if messages else {}
    sender = message.get("sender", {})

    # Iniciar evento de ejecución
    await event_emitter.start_execution(
        execution_id=execution_id,
        identifier=sender.get("identifier", ""),
        user_name=sender.get("name", ""),
        conversation_id=message.get("conversation_id", 0),
        chat_input=message.get("content", "")[:200],
    )

    try:
        preview_in = json.dumps(payload, ensure_ascii=False)[:500]
        await event_emitter.update_payload_in_preview(execution_id, preview_in)
    except Exception:
        pass

    try:
        final_state = cast(ChatbotState, await chatbot_graph.ainvoke(initial_state))

        await event_emitter.complete_execution(
            execution_id=execution_id,
            ai_response=final_state.get("ai_response"),
            error=final_state.get("error"),
        )

        logger.info(
            "Grafo ejecutado exitosamente",
            execution_id=execution_id,
            should_continue=final_state.get("should_continue"),
        )

        return dict(final_state)

    except Exception as e:
        await event_emitter.complete_execution(
            execution_id=execution_id,
            error=str(e),
        )
        logger.error("Error ejecutando grafo", error=str(e))
        return {**dict(initial_state), "error": str(e), "should_continue": False}


async def enqueue_chatbot(payload: dict) -> str:
    execution_id = str(uuid.uuid4())
    body = payload.get("body", payload)
    conversation = body.get("conversation", {})
    messages = conversation.get("messages", [{}])
    message = messages[0] if messages else {}
    sender = message.get("sender", {})

    preview_in = None
    try:
        preview_in = json.dumps(payload, ensure_ascii=False)[:500]
    except Exception:
        preview_in = None

    evt = ExecutionEvent(
        execution_id=execution_id,
        status=NodeStatus.PENDING,
        identifier=sender.get("identifier", ""),
        user_name=sender.get("name", ""),
        conversation_id=message.get("conversation_id", 0),
        chat_input=(message.get("content", "") or "")[:200],
        payload_in_preview=preview_in,
    )
    await event_emitter.emit({"type": "execution_queued", "data": evt.model_dump(mode="json")})

    try:
        await redis_client.stream_group_create(
            settings.execution_stream_key, settings.execution_stream_group
        )
    except Exception:
        pass
    await redis_client.stream_add(
        settings.execution_stream_key,
        {
            "execution_id": execution_id,
            "payload": json.dumps(payload, ensure_ascii=False),
            "received_at": str(time.time()),
        },
        maxlen=5000,
    )
    return execution_id


async def _consume_loop(worker_idx: int) -> None:
    global _consumer_base
    if _consumer_base is None:
        host = socket.gethostname()
        _consumer_base = f"{host}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
    consumer = f"{_consumer_base}:{worker_idx}"
    stop = _worker_stop
    while True:
        if stop is not None and stop.is_set():
            return
        try:
            items = await redis_client.stream_read_group(
                settings.execution_stream_key,
                settings.execution_stream_group,
                consumer,
                count=1,
                block_ms=2000,
            )
        except Exception:
            await asyncio.sleep(0.5)
            continue

        if not items:
            continue
        try:
            stream_name, messages = items[0]
        except Exception:
            continue
        for message_id, fields in messages:
            eid = None
            payload_raw = None
            try:
                eid = fields.get("execution_id")
                payload_raw = fields.get("payload")
            except Exception:
                eid = None
                payload_raw = None
            if not eid or not payload_raw:
                try:
                    await redis_client.stream_ack(
                        stream_name, settings.execution_stream_group, message_id
                    )
                except Exception:
                    pass
                continue

            try:
                payload = json.loads(payload_raw)
            except Exception:
                payload = {"body": {"event": "invalid", "conversation": {"messages": []}}}

            try:
                await run_chatbot(payload, execution_id=eid)
            finally:
                try:
                    await redis_client.stream_ack(
                        stream_name, settings.execution_stream_group, message_id
                    )
                except Exception:
                    pass


async def start_worker_pool() -> None:
    global _worker_stop, _worker_tasks
    if _worker_tasks:
        return
    if not settings.execution_queue_enabled:
        return
    if settings.execution_role not in {"all", "worker"}:
        return
    _worker_stop = asyncio.Event()
    try:
        await redis_client.stream_group_create(
            settings.execution_stream_key, settings.execution_stream_group
        )
    except Exception:
        pass
    n = max(1, int(settings.execution_worker_concurrency or 1))
    _worker_tasks = [asyncio.create_task(_consume_loop(i)) for i in range(n)]


async def stop_worker_pool() -> None:
    global _worker_tasks, _worker_stop
    if _worker_stop is not None:
        _worker_stop.set()
    for t in list(_worker_tasks):
        try:
            t.cancel()
        except Exception:
            pass
    _worker_tasks = []
    _worker_stop = None


async def get_queue_status() -> dict:
    stream_len = None
    consumers = None
    pending = None
    try:
        stream_len = await redis_client.stream_len(settings.execution_stream_key)
    except Exception:
        stream_len = None
    try:
        consumers = await redis_client.stream_info_consumers(
            settings.execution_stream_key, settings.execution_stream_group
        )
    except Exception:
        consumers = None
    try:
        pending = await redis_client.stream_pending_summary(
            settings.execution_stream_key, settings.execution_stream_group
        )
    except Exception:
        pending = None
    return {
        "queue_enabled": settings.execution_queue_enabled,
        "role": settings.execution_role,
        "stream": settings.execution_stream_key,
        "group": settings.execution_stream_group,
        "stream_len": stream_len,
        "consumers": consumers,
        "pending": pending,
        "worker_concurrency": settings.execution_worker_concurrency,
    }


def get_graph_diagram() -> str:
    """Genera un diagrama Mermaid del grafo."""
    try:
        diagram = chatbot_graph.get_graph().draw_mermaid()
        return diagram if isinstance(diagram, str) else str(diagram)
    except Exception as e:
        logger.warning("No se pudo generar diagrama", error=str(e))
        return "# Error generando diagrama"
