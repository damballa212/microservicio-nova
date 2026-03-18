"""
Router de Testing.

Endpoints dedicados para probar el chatbot sin depender de un proveedor específico.
Incluye chat de pruebas con FLUJO COMPLETO, ejecución de nodos individuales.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.buffer.buffer_manager import buffer_manager
from src.config.prompts import get_system_prompt
from src.events.emitter import event_emitter
from src.memory.conversation_memory import conversation_memory
from src.models.state import ChatbotState, create_initial_state
from src.nodes.ai_agent import generate_response
from src.nodes.buffer import add_to_buffer, check_buffer_status
from src.nodes.escalation import classify_escalation, escalate_to_human
from src.nodes.formatter import format_response
from src.nodes.knowledge import (
    lookup_inventory_sheets,
    merge_knowledge,
    plan_knowledge,
    retrieve_docs_rag,
)
from src.nodes.multimodal import process_multimodal
from src.nodes.nlu import classify_intent, classify_intent_llm, score_lead, score_lead_llm

# Importar nodos
from src.nodes.validation import (
    check_bot_state,
    extract_message_data,
    validate_event,
    validate_sender,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

test_router = APIRouter(prefix="/test", tags=["Testing"])


# === Modelos ===


class ChatTestRequest(BaseModel):
    message: str = Field(description="Mensaje del usuario")
    user_name: str = Field(default="Test User")
    session_id: str | None = None
    vertical_id: str = Field(default="restaurante", description="Nicho a probar")
    empresa_config: dict[str, Any] = Field(default_factory=dict, description="Configuración dinámica de la empresa")


class ChatTestResponse(BaseModel):
    session_id: str
    user_message: str
    ai_response: str
    formatted_parts: list[str]
    execution_time_ms: float
    nodes_executed: list[str]


class PromptBuildRequest(BaseModel):
    vertical_id: str = Field(default="restaurante")
    empresa_config: dict[str, Any] = Field(default_factory=dict)

class PromptBuildResponse(BaseModel):
    system_prompt: str


class NodeTestRequest(BaseModel):
    state: dict[str, Any] = Field(description="Estado inicial")


class NodeTestResponse(BaseModel):
    node_name: str
    success: bool
    input_state: dict[str, Any]
    output_state: dict[str, Any]
    execution_time_ms: float
    error: str | None = None


class NodeInfo(BaseModel):
    name: str
    description: str
    required_fields: list[str]
    output_fields: list[str]


# === Nodos disponibles ===

NODE_FUNCTIONS = {
    "validate_event": validate_event,
    "validate_sender": validate_sender,
    "check_bot_state": check_bot_state,
    "extract_data": extract_message_data,
    "add_to_buffer": add_to_buffer,
    "check_buffer_status": check_buffer_status,
    "process_multimodal": process_multimodal,
    "classify_intent": classify_intent,
    "classify_intent_llm": classify_intent_llm,
    "plan_knowledge": plan_knowledge,
    "lookup_inventory_sheets": lookup_inventory_sheets,
    "retrieve_docs_rag": retrieve_docs_rag,
    "merge_knowledge": merge_knowledge,
    "score_lead": score_lead,
    "score_lead_llm": score_lead_llm,
    "generate_response": generate_response,
    "format_response": format_response,
    "classify_escalation": classify_escalation,
    "escalate_to_human": escalate_to_human,
}

NODE_INFO = {
    "validate_event": NodeInfo(
        name="validate_event",
        description="Valida que el evento sea 'message_created'",
        required_fields=["raw_payload"],
        output_fields=["event_type", "should_continue"],
    ),
    "validate_sender": NodeInfo(
        name="validate_sender",
        description="Valida que el remitente sea un Contact",
        required_fields=["raw_payload"],
        output_fields=["sender_type", "should_continue"],
    ),
    "check_bot_state": NodeInfo(
        name="check_bot_state",
        description="Verifica que el bot esté activo",
        required_fields=["raw_payload"],
        output_fields=["bot_state", "should_continue"],
    ),
    "extract_data": NodeInfo(
        name="extract_data",
        description="Extrae datos del mensaje",
        required_fields=["raw_payload"],
        output_fields=["identifier", "user_name", "phone_number"],
    ),
    "process_multimodal": NodeInfo(
        name="process_multimodal",
        description="Procesa contenido multimodal",
        required_fields=["identifier"],
        output_fields=["chat_input", "info_imagen"],
    ),
    "classify_intent": NodeInfo(
        name="classify_intent",
        description="Clasifica intención por heurística y aplica labels",
        required_fields=["chat_input"],
        output_fields=["actions.intencion_detectada", "actions.apply_labels"],
    ),
    "classify_intent_llm": NodeInfo(
        name="classify_intent_llm",
        description="Clasifica intención con LLM (fallback heurístico)",
        required_fields=["chat_input"],
        output_fields=["actions.intencion_detectada", "actions.apply_labels"],
    ),
    "plan_knowledge": NodeInfo(
        name="plan_knowledge",
        description="Planifica fuentes de conocimiento (docs/sheets)",
        required_fields=["chat_input"],
        output_fields=["knowledge_plan"],
    ),
    "lookup_inventory_sheets": NodeInfo(
        name="lookup_inventory_sheets",
        description="Consulta inventario en Google Sheets (si aplica)",
        required_fields=["knowledge_plan", "google_sheet_id", "inventory_query"],
        output_fields=["sheets_result"],
    ),
    "retrieve_docs_rag": NodeInfo(
        name="retrieve_docs_rag",
        description="Recupera documentos RAG por tenant desde Flowify (si aplica)",
        required_fields=["knowledge_plan", "tenant_id"],
        output_fields=["rag_docs"],
    ),
    "merge_knowledge": NodeInfo(
        name="merge_knowledge",
        description="Normaliza evidencia de conocimiento para el prompt",
        required_fields=["rag_docs"],
        output_fields=["rag_docs", "sheets_result"],
    ),
    "score_lead": NodeInfo(
        name="score_lead",
        description="Califica lead con reglas mínimas",
        required_fields=["chat_input"],
        output_fields=["actions.lead_calificado", "actions.apply_labels"],
    ),
    "score_lead_llm": NodeInfo(
        name="score_lead_llm",
        description="Califica lead con LLM (fallback reglas)",
        required_fields=["chat_input"],
        output_fields=["actions.lead_calificado", "actions.apply_labels"],
    ),
    "generate_response": NodeInfo(
        name="generate_response",
        description="Genera respuesta con el Agente IA",
        required_fields=["chat_input", "identifier"],
        output_fields=["ai_response"],
    ),
    "format_response": NodeInfo(
        name="format_response",
        description="Divide respuesta para WhatsApp",
        required_fields=["ai_response"],
        output_fields=["formatted_parts"],
    ),
    "classify_escalation": NodeInfo(
        name="classify_escalation",
        description="Clasifica si necesita escalamiento",
        required_fields=["chat_input", "ai_response"],
        output_fields=["needs_escalation"],
    ),
    "escalate_to_human": NodeInfo(
        name="escalate_to_human",
        description="Ejecuta escalamiento (tagging + bot off)",
        required_fields=["needs_escalation"],
        output_fields=["actions"],
    ),
}


# === Helper para ejecutar nodo con eventos ===


async def run_node_with_events(
    node_name: str,
    node_func: Any,
    state: ChatbotState,
    execution_id: str,
    delay_ms: int = 100,
) -> ChatbotState:
    """Ejecuta un nodo emitiendo eventos de inicio/fin para el dashboard."""
    await event_emitter.emit_node_start(node_name, execution_id)

    # Pequeño delay para que se vea la animación
    await asyncio.sleep(delay_ms / 1000)

    start = datetime.now()

    if asyncio.iscoroutinefunction(node_func):
        result = await node_func(state)
    else:
        result = node_func(state)

    duration = (datetime.now() - start).total_seconds() * 1000
    metrics = None
    try:
        metrics = result.get("_node_metrics") if isinstance(result, dict) else None
        if isinstance(result, dict) and "_node_metrics" in result:
            del result["_node_metrics"]
    except Exception:
        metrics = None
    await event_emitter.emit_node_complete(node_name, execution_id, f"{duration:.0f}ms", metrics)

    return cast(ChatbotState, result) if isinstance(result, dict) else state


# === Endpoints ===


@test_router.get("/nodes", response_model=list[NodeInfo])
async def list_testable_nodes():
    """Lista todos los nodos disponibles para testing."""
    return list(NODE_INFO.values())


@test_router.post("/node/{node_name}", response_model=NodeTestResponse)
async def test_node(node_name: str, request: NodeTestRequest):
    """Prueba un nodo individual."""
    if node_name not in NODE_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Nodo '{node_name}' no encontrado")

    node_func = NODE_FUNCTIONS[node_name]
    state = create_initial_state({})
    state = cast(ChatbotState, {**state, **request.state})
    state["_execution_id"] = str(uuid.uuid4())
    state["_sandbox_mode"] = True

    start_time = datetime.now()

    try:
        if asyncio.iscoroutinefunction(node_func):
            result_state = await node_func(state)
        else:
            result_state = node_func(state)

        duration = (datetime.now() - start_time).total_seconds() * 1000
        output_state = {k: v for k, v in result_state.items() if not k.startswith("_")}

        return NodeTestResponse(
            node_name=node_name,
            success=True,
            input_state=request.state,
            output_state=output_state,
            execution_time_ms=duration,
        )
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds() * 1000
        return NodeTestResponse(
            node_name=node_name,
            success=False,
            input_state=request.state,
            output_state={},
            execution_time_ms=duration,
            error=str(e),
        )


@test_router.post("/chat", response_model=ChatTestResponse)
async def test_chat(request: ChatTestRequest):
    """
    Prueba el chat ejecutando el FLUJO COMPLETO de nodos.

    Ejecuta TODOS los nodos en secuencia para ver la animación en tiempo real:
    validate_event → validate_sender → check_bot_state → extract_data →
    add_to_buffer → check_buffer_status → process_multimodal →
    generate_response → format_response → classify_escalation
    """
    session_id = request.session_id or f"test_{uuid.uuid4().hex[:8]}"
    execution_id = str(uuid.uuid4())

    start_time = datetime.now()
    nodes_executed = []

    logger.info("Iniciando test de chat COMPLETO", session_id=session_id)

    # Crear payload simulado de Chatwoot
    fake_payload = {
        "event": "message_created",
        "message_type": "incoming",
        "vertical_id": request.vertical_id,
        "empresa_config": request.empresa_config,
        "conversation": {
            "id": 12345,
            "status": "open",
            "custom_attributes": {"bot_status": "ON"},
            "contact_inbox": {"contact_id": 99999},
            "messages": [
                {
                    "id": 1,
                    "account_id": 1,
                    "conversation_id": 12345,
                    "content": request.message,
                    "content_type": "text",
                    "sender_type": "Contact",
                    "sender": {
                        "id": 99999,
                        "name": request.user_name,
                        "identifier": "test_user",
                        "phone_number": "",
                        "custom_attributes": {},
                    },
                    "created_at": datetime.now().isoformat() + "Z",
                    "source_id": f"test_{uuid.uuid4().hex[:8]}",
                    "attachments": [],
                }
            ],
            "meta": {"sender": {"id": 99999, "name": request.user_name}},
        },
        "account": {"id": 1},
    }

    # Estado inicial
    state: ChatbotState = create_initial_state(fake_payload)
    state["identifier"] = session_id
    state["_execution_id"] = execution_id
    state["_sandbox_mode"] = True

    # Iniciar evento de ejecución
    await event_emitter.start_execution(
        execution_id=execution_id,
        identifier=session_id,
        user_name=request.user_name,
        conversation_id=12345,
        chat_input=request.message[:100],
    )

    try:
        # === EJECUTAR TODOS LOS NODOS EN SECUENCIA ===

        # 1. Validar Evento
        state = await run_node_with_events(
            "validate_event", validate_event, state, execution_id, 150
        )
        nodes_executed.append("validate_event")

        # 2. Validar Remitente
        state = await run_node_with_events(
            "validate_sender", validate_sender, state, execution_id, 150
        )
        nodes_executed.append("validate_sender")

        # 3. Estado del Bot
        state = await run_node_with_events(
            "check_bot_state", check_bot_state, state, execution_id, 150
        )
        nodes_executed.append("check_bot_state")

        # 4. Extraer Datos
        state = await run_node_with_events(
            "extract_data", extract_message_data, state, execution_id, 150
        )
        nodes_executed.append("extract_data")
        state["identifier"] = session_id  # Mantener session_id de prueba

        # 5. Agregar a Buffer (simular)
        await event_emitter.emit_node_start("add_to_buffer", execution_id)
        await asyncio.sleep(0.15)
        from src.models.state import MessageData

        msg_data = MessageData(
            content=request.message,
            source_id=f"test_{uuid.uuid4().hex[:8]}",
            content_type="text",
            attachments=[],
            created_at=datetime.now().isoformat() + "Z",
        )
        await buffer_manager.add_message(session_id, msg_data.model_dump())
        await event_emitter.emit_node_complete("add_to_buffer", execution_id, "1 mensaje")
        nodes_executed.append("add_to_buffer")

        # 6. Estado del Buffer
        await event_emitter.emit_node_start("check_buffer_status", execution_id)
        await asyncio.sleep(0.15)
        state["buffer_action"] = "process"
        await event_emitter.emit_node_complete("check_buffer_status", execution_id, "process")
        nodes_executed.append("check_buffer_status")

        # 7. Procesar Multimodal
        state = await run_node_with_events(
            "process_multimodal", process_multimodal, state, execution_id, 200
        )
        nodes_executed.append("process_multimodal")

        # Asegurar que chat_input tiene contenido
        if not state.get("chat_input"):
            state["chat_input"] = request.message

        # 7.1 Clasificar Intención (LLM)
        state = await run_node_with_events(
            "classify_intent", classify_intent_llm, state, execution_id, 150
        )
        nodes_executed.append("classify_intent")

        # 7.2 Score Lead (LLM)
        state = await run_node_with_events(
            "score_lead", score_lead_llm, state, execution_id, 150
        )
        nodes_executed.append("score_lead")

        # 8. Agente IA (el más importante)
        state = await run_node_with_events(
            "generate_response", generate_response, state, execution_id, 0
        )
        nodes_executed.append("generate_response")

        # 9. Formatear Respuesta
        state = await run_node_with_events(
            "format_response", format_response, state, execution_id, 100
        )
        nodes_executed.append("format_response")

        # 10. Clasificar Escalamiento
        # Ahora usamos la lógica REAL, no hardcodeada
        prev_escalation = state.get("needs_escalation")
        # Si el AI ya marcó escalamiento (flag directa), respetarla. Si no, clasificar.
        if not prev_escalation:
             state = await run_node_with_events(
                "classify_escalation", classify_escalation, state, execution_id, 150
            ) 
        else:
             # Simular paso por el nodo si ya venía marcado (raro, pero posible)
             await event_emitter.emit_node_start("classify_escalation", execution_id)
             await asyncio.sleep(0.15)
             await event_emitter.emit_node_complete("classify_escalation", execution_id, "YES")

        nodes_executed.append("classify_escalation")
        
        # 10.5 Escalamiento Condicional
        if state.get("needs_escalation"):
            state = await run_node_with_events(
                "escalate_to_human", escalate_to_human, state, execution_id, 150
            )
            nodes_executed.append("escalate_to_human")

        # 11. Enviar Mensajes (simulado - no envía realmente)
        await event_emitter.emit_node_start("send_messages", execution_id)
        await asyncio.sleep(0.2)
        await event_emitter.emit_node_complete("send_messages", execution_id, "Sandbox")
        nodes_executed.append("send_messages")

        duration = (datetime.now() - start_time).total_seconds() * 1000

        # Completar ejecución
        await event_emitter.complete_execution(
            execution_id=execution_id,
            ai_response=state.get("ai_response"),
        )

        return ChatTestResponse(
            session_id=session_id,
            user_message=request.message,
            ai_response=state.get("ai_response", ""),
            formatted_parts=state.get("formatted_parts", []),
            execution_time_ms=duration,
            nodes_executed=nodes_executed,
        )

    except Exception as e:
        await event_emitter.complete_execution(
            execution_id=execution_id,
            error=str(e),
        )
        logger.error("Error en test de chat", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@test_router.post("/prompt", response_model=PromptBuildResponse)
async def build_prompt(request: PromptBuildRequest):
    try:
        prompt = get_system_prompt(request.vertical_id, request.empresa_config)
        return PromptBuildResponse(system_prompt=prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@test_router.delete("/memory/{session_id}")
async def clear_test_memory(session_id: str):
    """Limpia la memoria de una sesión de prueba."""
    await conversation_memory.clear_history(session_id)
    await buffer_manager.clear(session_id)
    return {"message": f"Memoria de '{session_id}' eliminada"}


@test_router.get("/memory/{session_id}")
async def get_test_memory(session_id: str):
    """Obtiene el historial de una sesión."""
    history = await conversation_memory.get_history(session_id)
    return {"session_id": session_id, "history": history}
