"use client";

import React, { useMemo, useRef, useEffect, useState } from "react";
import { useDashboard } from "../providers/DashboardProvider";
import { cn } from "@/lib/utils";

// ============================================================================
// DEFINICIÓN DE PIPELINE - Estructura visual del flujo
// ============================================================================

interface PipelineNode {
    id: string;
    label: string;
    sublabel: string;
    type?: "decision" | "resource" | "brain";
}

interface PipelinePhase {
    name: string;
    color: string;
    nodes: PipelineNode[];
}

const PIPELINE_PHASES: PipelinePhase[] = [
    {
        name: "INGRESS",
        color: "#f472b6",
        nodes: [
            { id: "webhook_entry", label: "Webhook In", sublabel: "Gateway" },
            { id: "validate_event", label: "Security", sublabel: "Validation" },
            { id: "validate_sender", label: "SDR Filter", sublabel: "Sender" },
            { id: "check_bot_state", label: "State", sublabel: "Status" },
            { id: "extract_data", label: "Parser", sublabel: "Extract" },
        ]
    },
    {
        name: "LOGIC",
        color: "#2dd4bf",
        nodes: [
            { id: "add_to_buffer", label: "Buffer", sublabel: "Queue" },
            { id: "check_buffer_status", label: "Gatekeeper", sublabel: "Anti-Spam", type: "decision" },
            { id: "process_multimodal", label: "MultiModal", sublabel: "Vision/Audio" },
        ]
    },
    {
        name: "NEURAL CORE",
        color: "#a855f7",
        nodes: [
            { id: "classify_intent", label: "Intent Map", sublabel: "NLU" },
            { id: "plan_knowledge", label: "Planner", sublabel: "Reasoning" },
            { id: "ai_orchestrator", label: "Core AI", sublabel: "GPT-4o", type: "brain" },
            { id: "score_lead", label: "SDR Score", sublabel: "Lead Qual" },
        ]
    },
    {
        name: "TOOLS",
        color: "#10b981",
        nodes: [
            { id: "tool_sheets", label: "Inventory", sublabel: "G-Sheets", type: "resource" },
            { id: "tool_knowledge", label: "RAG", sublabel: "Vector DB", type: "resource" },
            { id: "tool_semantic_memory", label: "Semantic", sublabel: "Episodes", type: "resource" },
            { id: "merge_knowledge", label: "Fusion", sublabel: "Context" },
        ]
    },
    {
        name: "EGRESS",
        color: "#fbbf24",
        nodes: [
            { id: "format_response", label: "Responder", sublabel: "Format" },
            { id: "classify_escalation", label: "Escalator", sublabel: "Check", type: "decision" },
            { id: "escalate_to_human", label: "Human", sublabel: "Handoff" },
            { id: "post_to_outbound_webhook", label: "Flowify", sublabel: "Outbound" },
        ]
    },
];

// ============================================================================
// MAPEO BACKEND → VISUAL (Completo)
// ============================================================================

const NODE_MAPPING: Record<string, string> = {
    // Mapeos directos (el backend usa el mismo nombre)
    "webhook_entry": "webhook_entry",
    "validate_event": "validate_event",
    "validate_sender": "validate_sender",
    "check_bot_state": "check_bot_state",
    "extract_data": "extract_data",
    "add_to_buffer": "add_to_buffer",
    "check_buffer_status": "check_buffer_status",
    "process_multimodal": "process_multimodal",
    "classify_intent": "classify_intent",
    "plan_knowledge": "plan_knowledge",
    "ai_orchestrator": "ai_orchestrator",
    "score_lead": "score_lead",
    "tool_sheets": "tool_sheets",
    "tool_knowledge": "tool_knowledge",
    "tool_semantic_memory": "tool_semantic_memory",
    "merge_knowledge": "merge_knowledge",
    "format_response": "format_response",
    "classify_escalation": "classify_escalation",
    "escalate_to_human": "escalate_to_human",
    "post_to_outbound_webhook": "post_to_outbound_webhook",

    // Mapeos alternativos (nombres del backend que difieren)
    "generate_response": "ai_orchestrator",
    "retrieve_documents": "tool_knowledge",
    "lookup_inventory": "tool_sheets",
    "validate_webhook": "validate_event",
    "check_sender": "validate_sender",
    "extract_message": "extract_data",
    "buffer_message": "add_to_buffer",
    "check_buffer": "check_buffer_status",
    "process_media": "process_multimodal",
    "plan_retrieval": "plan_knowledge",
    "format_output": "format_response",
    "check_escalation": "classify_escalation",
    "handoff_human": "escalate_to_human",
    "send_webhook": "post_to_outbound_webhook",
    "semantic_memory": "tool_semantic_memory",
    "knowledge_fusion": "merge_knowledge",
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

export const NeuralGraph = () => {
    const { executions = {}, activeExecutionId } = useDashboard();
    const containerRef = useRef<HTMLDivElement>(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

    // Resize observer
    useEffect(() => {
        if (!containerRef.current) return;
        const ro = new ResizeObserver((entries) => {
            const { width, height } = entries[0].contentRect;
            setDimensions({ width, height });
        });
        ro.observe(containerRef.current);
        return () => ro.disconnect();
    }, []);

    // Calcular nodos activos y completados
    const nodeStates = useMemo(() => {
        const active = new Set<string>();
        const completed = new Set<string>();
        const errors = new Set<string>();

        let ex = activeExecutionId ? executions[activeExecutionId] : null;
        if (!ex) {
            const sorted = Object.values(executions).sort((a, b) =>
                new Date(b.started_at || 0).getTime() - new Date(a.started_at || 0).getTime()
            );
            ex = sorted.find(e => e.status === "RUNNING") || sorted[0];
        }

        if (ex) {
            const exStatus = (ex.status || "").toUpperCase();

            // Marcar nodo actual como activo
            if (exStatus === "RUNNING" && ex.current_node) {
                const mappedNode = NODE_MAPPING[ex.current_node.toLowerCase()];
                if (mappedNode) {
                    active.add(mappedNode);
                }
            }

            // Si está RUNNING pero no hay current_node, el primer nodo está activo
            if (exStatus === "RUNNING" && !ex.current_node && Object.keys(ex.nodes).length === 0) {
                active.add("webhook_entry");
            }

            // Marcar nodos completados/errores
            Object.entries(ex.nodes).forEach(([nodeName, nodeData]) => {
                const status = (nodeData.status || "").toUpperCase();
                const mappedNode = NODE_MAPPING[nodeName.toLowerCase()] || nodeName.toLowerCase();

                if (status === "COMPLETED") {
                    completed.add(mappedNode);
                } else if (status === "ERROR") {
                    errors.add(mappedNode);
                }
            });
        }

        return { active, completed, errors };
    }, [executions, activeExecutionId]);

    // Calcular layout
    const phaseWidth = dimensions.width / PIPELINE_PHASES.length;
    const nodeHeight = 56;
    const nodeGap = 12;

    // Determinar estado del pipeline basado en la ejecución activa
    const getStatusLabel = () => {
        // Si hay nodos activos (ejecución en progreso)
        if (nodeStates.active.size > 0) return "PROCESSING";

        // Si hay errores en la ejecución actual
        if (nodeStates.errors.size > 0) return "ERROR";

        // Si hay nodos completados, verificar si es una ejecución histórica
        if (nodeStates.completed.size > 0) {
            const ex = activeExecutionId ? executions[activeExecutionId] : null;
            // Solo mostrar COMPLETED si hay una ejecución activa reciente
            if (ex && ex.status === "COMPLETED") {
                return "COMPLETED";
            }
        }

        return "READY";
    };

    const getStatusColor = () => {
        if (nodeStates.active.size > 0) return "text-indigo-400";
        if (nodeStates.errors.size > 0) return "text-red-400";
        if (nodeStates.completed.size > 0) {
            const ex = activeExecutionId ? executions[activeExecutionId] : null;
            if (ex && ex.status === "COMPLETED") {
                return "text-emerald-400";
            }
        }
        return "text-slate-500";
    };

    return (
        <div ref={containerRef} className="w-full h-full bg-[#0f172a] relative overflow-hidden">
            {/* Grid Background */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:40px_40px] opacity-20 pointer-events-none" />

            {/* Header */}
            <div className="absolute top-4 left-4 text-xs font-mono text-slate-500 z-10">
                NOVA PIPELINE • <span className={getStatusColor()}>{getStatusLabel()}</span>
            </div>

            {/* Pipeline Visualization */}
            <div className="absolute inset-0 flex items-center justify-center p-8">
                <div className="flex gap-2 w-full max-w-[1400px]">
                    {PIPELINE_PHASES.map((phase, phaseIndex) => (
                        <PhaseColumn
                            key={phase.name}
                            phase={phase}
                            nodeStates={nodeStates}
                            isLast={phaseIndex === PIPELINE_PHASES.length - 1}
                        />
                    ))}
                </div>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 right-4 flex gap-4 text-[10px] font-mono text-slate-500">
                <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-slate-700" />
                    <span>IDLE</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                    <span>ACTIVE</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span>DONE</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-red-500" />
                    <span>ERROR</span>
                </div>
            </div>
        </div>
    );
};

// ============================================================================
// COMPONENTES AUXILIARES
// ============================================================================

interface PhaseColumnProps {
    phase: PipelinePhase;
    nodeStates: { active: Set<string>; completed: Set<string>; errors: Set<string> };
    isLast: boolean;
}

const PhaseColumn = ({ phase, nodeStates, isLast }: PhaseColumnProps) => {
    return (
        <div className="flex-1 flex flex-col">
            {/* Phase Header */}
            <div
                className="text-[10px] font-bold tracking-wider mb-3 px-2 py-1 rounded"
                style={{ color: phase.color, backgroundColor: `${phase.color}10` }}
            >
                {phase.name}
            </div>

            {/* Nodes */}
            <div className="flex-1 flex flex-col gap-2">
                {phase.nodes.map((node, nodeIndex) => (
                    <NodeCard
                        key={node.id}
                        node={node}
                        phaseColor={phase.color}
                        isActive={nodeStates.active.has(node.id)}
                        isCompleted={nodeStates.completed.has(node.id)}
                        isError={nodeStates.errors.has(node.id)}
                    />
                ))}
            </div>
        </div>
    );
};

interface NodeCardProps {
    node: PipelineNode;
    phaseColor: string;
    isActive: boolean;
    isCompleted: boolean;
    isError: boolean;
}

const NodeCard = ({ node, phaseColor, isActive, isCompleted, isError }: NodeCardProps) => {
    const getStatusStyles = () => {
        if (isError) {
            return {
                border: "border-red-500/50",
                bg: "bg-red-500/10",
                glow: "shadow-[0_0_20px_rgba(239,68,68,0.3)]",
                indicator: "bg-red-500",
            };
        }
        if (isActive) {
            return {
                border: "border-indigo-500/70",
                bg: "bg-indigo-500/10",
                glow: "shadow-[0_0_25px_rgba(99,102,241,0.4)]",
                indicator: "bg-indigo-500 animate-pulse",
            };
        }
        if (isCompleted) {
            return {
                border: "border-emerald-500/40",
                bg: "bg-emerald-500/5",
                glow: "",
                indicator: "bg-emerald-500",
            };
        }
        return {
            border: "border-slate-700/50",
            bg: "bg-slate-900/50",
            glow: "",
            indicator: "bg-slate-700",
        };
    };

    const styles = getStatusStyles();
    const isBrain = node.type === "brain";
    const isDecision = node.type === "decision";
    const isResource = node.type === "resource";

    return (
        <div
            className={cn(
                "relative rounded-lg border px-3 py-2.5 transition-all duration-300",
                styles.border,
                styles.bg,
                styles.glow,
                isBrain && "ring-1 ring-purple-500/20",
            )}
        >
            {/* Top accent bar */}
            <div
                className="absolute top-0 left-0 right-0 h-[3px] rounded-t-lg"
                style={{ backgroundColor: isActive || isCompleted || isError ? styles.indicator.replace("bg-", "") : phaseColor, opacity: isActive || isCompleted ? 1 : 0.3 }}
            />

            {/* Status indicator */}
            <div className={cn("absolute -right-1 -top-1 w-2.5 h-2.5 rounded-full border-2 border-[#0f172a]", styles.indicator)} />

            {/* Content */}
            <div className="flex items-center gap-2">
                {/* Icon based on type */}
                <div className={cn(
                    "w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold",
                    isResource ? "bg-slate-800 text-slate-400" :
                        isDecision ? "bg-slate-800 text-amber-400 rotate-45" :
                            isBrain ? "bg-purple-900/50 text-purple-400" :
                                "bg-slate-800/50 text-slate-500"
                )}>
                    {isBrain ? "◆" : isDecision ? "◇" : isResource ? "▢" : "○"}
                </div>

                <div className="flex-1 min-w-0">
                    <div className="text-xs font-semibold text-slate-200 truncate">
                        {node.label}
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                        {node.sublabel}
                    </div>
                </div>
            </div>
        </div>
    );
};
