
"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode, useRef, useCallback, startTransition } from "react";

export type NodeStatus = "IDLE" | "RUNNING" | "COMPLETED" | "ERROR" | "SKIPPED";

export interface NodeEvent {
    node_name: string;
    status: NodeStatus;
    duration_ms?: number;
    error?: string;
    output_preview?: string;
}

export interface ExecutionEvent {
    execution_id: string;
    status: NodeStatus;
    identifier: string;
    user_name: string;
    nodes: Record<string, NodeEvent>;
    logs: LogEntry[];
    current_node?: string | null;
    started_at?: string;
    ai_response?: string;
    tokens?: number;
    cost?: number;
}

export interface LogEntry {
    timestamp: number | string;
    message: string;
    level?: string;
    node_name?: string;
}

interface DashboardContextType {
    isConnected: boolean;
    historyLoaded: boolean;
    executions: Record<string, ExecutionEvent>;
    activeExecutionId: string | null;
    setActiveExecutionId: (id: string | null) => void;
    recentLogs: LogEntry[];
    messages: { role: string; content: string }[];
    sendMessage: (msg: string) => void;
    resetSession: () => void;
    graphData: { nodes: Record<string, unknown>[]; links: Record<string, unknown>[] };
    modalExecution: ExecutionEvent | null;
    setModalExecution: (ex: ExecutionEvent | null) => void;
    // Testing Config
    verticalId: string;
    setVerticalId: (id: string) => void;
    tenantData: Record<string, string>;
    setTenantData: (data: Record<string, string>) => void;
    // Session Management
    sessionId: string;
}

const DashboardContext = createContext<DashboardContextType>({} as DashboardContextType);

export const useDashboard = () => useContext(DashboardContext);

export const DashboardProvider = ({ children }: { children: ReactNode }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [historyLoaded, setHistoryLoaded] = useState(false);
    const [executions, setExecutions] = useState<Record<string, ExecutionEvent>>({});
    const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null);
    const [recentLogs, setRecentLogs] = useState<LogEntry[]>([]);
    const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
    const [modalExecution, setModalExecution] = useState<ExecutionEvent | null>(null);
    const [sessionId, setSessionId] = useState<string>("");

    const mergeMessages = useCallback(
        (
            prev: { role: string; content: string }[],
            remote: { role: string; content: string }[],
        ): { role: string; content: string }[] => {
            const seen = new Set(prev.map((m) => `${m.role}|${m.content}`));
            const appended: { role: string; content: string }[] = [];
            for (const m of remote) {
                const key = `${m.role}|${m.content}`;
                if (!seen.has(key)) {
                    seen.add(key);
                    appended.push(m);
                }
            }
            return [...prev, ...appended];
        },
        []
    );

    // Testing System Default Configuration — campos vacíos por defecto.
    // El admin los configura desde el panel "SIMULATOR CONFIG" en la UI.
    // NUNCA poner datos ficticios aquí para no confundir al bot con info inventada.
    const [verticalId, setVerticalId] = useState("restaurante");
    const [tenantData, setTenantData] = useState<Record<string, string>>({
        nombre: "",
        giro: "",
        tono: "",
        ubicacion: "",
        horarios: "",
        reglas_reserva: "",
        google_sheet_id: "",
        delivery_info: "",
        metodos_pago: "",
        oferta: "",
        reglas: ""
    });


    // Graph Data structure for ForceGraph
    const [graphData] = useState<{ nodes: Record<string, unknown>[]; links: Record<string, unknown>[] }>({ nodes: [], links: [] });

    const wsParams = useRef<{
        url: string;
        reconnectInterval: number;
    }>({
        url: "", // Will be set in useEffect
        reconnectInterval: 3000,
    });

    const ws = useRef<WebSocket | null>(null);
    const reconnect = useRef<() => void>(() => { });
    const reconnectAttempts = useRef(0);
    const MAX_RECONNECT_ATTEMPTS = 10;
    const DEFAULT_API_HOST = process.env.NEXT_PUBLIC_API_HOST || 'localhost:8000';

    const handleEvent = useCallback((payload: unknown) => {
        const event = payload as { type: string; data: unknown };
        const { type, data } = event;

        if (type === "graph_definition") {
            return;
        }

        if (type === "execution_start" || type === "execution_queued") {
            const d = data as ExecutionEvent;
            setExecutions(prev => ({
                ...prev,
                [d.execution_id]: {
                    ...d,
                    status: ((d.status || "RUNNING").toUpperCase() as NodeStatus),
                    nodes: d.nodes || {},
                    logs: d.logs || []
                }
            }));
            setActiveExecutionId(d.execution_id);
        }

        if (type === "execution_complete") {
            const d = data as ExecutionEvent;
            setExecutions(prev => {
                const ex = prev[d.execution_id];
                if (!ex) return {
                    ...prev,
                    [d.execution_id]: { ...d, nodes: d.nodes || {}, logs: d.logs || [] }
                };
                return {
                    ...prev,
                    [d.execution_id]: {
                        ...ex,
                        ...d,
                        status: ("COMPLETED" as NodeStatus),
                        nodes: { ...ex.nodes, ...(d.nodes || {}) }
                    }
                };
            });

            if (d.ai_response) {
                setMessages(prev => {
                    const lastMsg = prev[prev.length - 1];
                    const content = d.ai_response as string;
                    if (lastMsg?.role === "assistant" && lastMsg.content === content) return prev;
                    return [...prev, { role: "assistant", content }];
                });
            }

            // Auto-reset visual después de 10 segundos para volver a estado READY
            const completedExecId = d.execution_id;
            setTimeout(() => {
                setActiveExecutionId(prev => {
                    // Solo resetear si sigue siendo la misma ejecución
                    if (prev === completedExecId) {
                        return null;
                    }
                    return prev;
                });
            }, 10000);
        }

        if (type === "execution_history") {
            const historyMap: Record<string, ExecutionEvent> = {};
            (data as ExecutionEvent[]).forEach((ex: ExecutionEvent) => {
                const normalizedStatus = (ex.status === "ERROR" ? "ERROR" : "COMPLETED");
                historyMap[ex.execution_id] = { ...ex, status: normalizedStatus };
            });
            setExecutions(prev => ({ ...prev, ...historyMap }));
            const arr = data as ExecutionEvent[];
            if (!activeExecutionId && arr.length > 0) setActiveExecutionId(arr[0].execution_id);
        }

        if (type === "execution_update") {
            const d = data as ExecutionEvent;
            setExecutions(prev => {
                const ex = prev[d.execution_id] || { execution_id: d.execution_id, status: "RUNNING", nodes: {}, logs: [] };
                const normalizedStatus = ((d.status || ex.status || "RUNNING").toUpperCase() as NodeStatus);
                return {
                    ...prev,
                    [d.execution_id]: {
                        ...ex,
                        ...d,
                        status: normalizedStatus,
                        nodes: { ...(ex.nodes || {}), ...(d.nodes || {}) },
                        logs: d.logs || ex.logs || []
                    }
                };
            });
        }

        if (type === "node_start") {
            const { execution_id, node } = data as { execution_id: string; node: NodeEvent };
            setExecutions(prev => {
                const ex = prev[execution_id] || { execution_id, status: "RUNNING", nodes: {}, logs: [] };
                const normalizedNode = {
                    ...node,
                    status: ((node.status || "RUNNING").toUpperCase() as NodeStatus)
                };
                return {
                    ...prev,
                    [execution_id]: {
                        ...ex,
                        current_node: normalizedNode.node_name,
                        nodes: {
                            ...ex.nodes,
                            [normalizedNode.node_name]: normalizedNode
                        }
                    }
                };
            });
        }

        if (type === "node_complete" || type === "node_error") {
            const { execution_id, node } = data as { execution_id: string; node: NodeEvent };
            setExecutions(prev => {
                const ex = prev[execution_id];
                if (!ex) return prev;
                const normalizedNode = {
                    ...node,
                    status: ((node.status || "COMPLETED").toUpperCase() as NodeStatus)
                };
                return {
                    ...prev,
                    [execution_id]: {
                        ...ex,
                        current_node: null,
                        nodes: {
                            ...ex.nodes,
                            [normalizedNode.node_name]: normalizedNode
                        }
                    }
                };
            });
        }

        if (type === "log" || type === "telemetry") {
            const d = data as Partial<LogEntry>;
            setRecentLogs(prev => {
                const exists = prev.some(l => l.timestamp === d.timestamp && l.message === d.message);
                if (exists) return prev;
                const entry: LogEntry = {
                    timestamp: d.timestamp ?? Date.now(),
                    message: d.message ?? "",
                    level: d.level,
                    node_name: d.node_name,
                };
                return [entry, ...prev].slice(0, 100);
            });
        }
    }, [activeExecutionId]);

    const connect = useCallback(() => {
        if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) return;

        console.log("Connecting to NOVA Dashboard WS...", wsParams.current.url);
        const socket = new WebSocket(wsParams.current.url);

        socket.onopen = () => {
            console.log("WS Connected");
            setIsConnected(true);
            reconnectAttempts.current = 0; // Reset on successful connection
        };

        socket.onclose = () => {
            console.log("WS Disconnected");
            setIsConnected(false);
            if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts.current++;
                console.log(`Reconnecting... attempt ${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS}`);
                setTimeout(() => reconnect.current(), wsParams.current.reconnectInterval);
            } else {
                console.error("Max WebSocket reconnect attempts reached. Giving up.");
            }
        };

        socket.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                handleEvent(payload);
            } catch (e) {
                console.error("WS Parse Error", e);
            }
        };

        socket.onerror = (e) => {
            console.error("WS Error", e);
        };

        ws.current = socket;
    }, [handleEvent]);



    const loadHistory = useCallback(async () => {
        if (!sessionId) return; // No cargar sin sessionId
        try {
            const isBrowser = typeof window !== 'undefined';
            const protocol = isBrowser ? window.location.protocol : 'http:';
            const localHost = isBrowser ? `${window.location.hostname}:8000` : DEFAULT_API_HOST;

            let API_BASE = "";
            if (process.env.NEXT_PUBLIC_API_URL) {
                API_BASE = process.env.NEXT_PUBLIC_API_URL;
            } else {
                API_BASE = `${protocol}//${localHost}`;
            }

            // Load Chat History for current session
            const chatRes = await fetch(`${API_BASE}/test/memory/${sessionId}`);
            const chatData = await chatRes.json();
            if (chatData.history) {
                startTransition(() => {
                    const remote = chatData.history.map((m: { role: string; content: string }) => ({
                        role: m.role,
                        content: m.content,
                    }));
                    setMessages((prev) => mergeMessages(prev, remote));
                });
            }

            // Load Executions History (global)
            const execRes = await fetch(`${API_BASE}/metrics/executions`);
            const execData = await execRes.json();
            // New structure: { active: [], recent: [] }
            const allExecutions = [...(execData.active || []), ...(execData.recent || [])];
            if (allExecutions.length > 0) {
                const historyMap: Record<string, ExecutionEvent> = {};
                allExecutions.forEach((ex: ExecutionEvent) => {
                    const normalizedStatus = (ex.status === "ERROR" ? "ERROR" : "COMPLETED");
                    historyMap[ex.execution_id] = { ...ex, status: normalizedStatus };
                });
                startTransition(() => {
                    setExecutions(prev => ({ ...prev, ...historyMap }));
                    // NO auto-seleccionar ejecución histórica - mantener pipeline en READY
                });
            }

            // Load Global Logs
            const logRes = await fetch(`${API_BASE}/metrics/logs`);
            const logData = await logRes.json();
            if (logData.logs) {
                startTransition(() => {
                    setRecentLogs(logData.logs.reverse()); // Show newest first
                });
            }
            startTransition(() => { setHistoryLoaded(true); });
        } catch (e) {
            console.error("Failed to load history", e);
            startTransition(() => { setHistoryLoaded(true); });
        }
    }, [DEFAULT_API_HOST, mergeMessages, sessionId]);

    // Inicializar sessionId desde localStorage o generar nuevo
    useEffect(() => {
        const stored = typeof window !== 'undefined' ? localStorage.getItem('nova_session_id') : null;
        if (stored) {
            setSessionId(stored);
        } else {
            const newId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            if (typeof window !== 'undefined') {
                localStorage.setItem('nova_session_id', newId);
            }
            setSessionId(newId);
        }
    }, []);

    // Conectar WebSocket al iniciar
    useEffect(() => {
        reconnect.current = connect;
        // Set dynamic WS URL on client side
        const isHTTPS = typeof window !== 'undefined' && window.location.protocol === 'https:';
        if (typeof window !== 'undefined') {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`;
            // Strip protocol to get host
            const host = apiBase.replace(/^https?:\/\//, '');
            const isSecure = apiBase.startsWith('https') || window.location.protocol === 'https:';
            wsParams.current.url = `${isSecure ? 'wss:' : 'ws:'}//${host}/ws/dashboard`;
        }

        connect();
        return () => {
            ws.current?.close();
        };
    }, [connect]);

    // Cargar historial cuando sessionId esté disponible
    useEffect(() => {
        if (sessionId) {
            startTransition(() => { void loadHistory(); });
        }
    }, [sessionId, loadHistory]);

    const sendMessage = async (msg: string) => {
        if (!historyLoaded || !sessionId) return;
        // Optimistic update
        setMessages(prev => [...prev, { role: "user", content: msg }]);

        try {
            const isBrowser = typeof window !== 'undefined';
            const protocol = isBrowser ? window.location.protocol : 'http:';
            const localHost = isBrowser ? `${window.location.hostname}:8000` : DEFAULT_API_HOST;

            let API_BASE = "";
            if (process.env.NEXT_PUBLIC_API_URL) {
                API_BASE = process.env.NEXT_PUBLIC_API_URL;
            } else {
                API_BASE = `${protocol}//${localHost}`;
            }

            await fetch(`${API_BASE}/test/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: msg,
                    user_name: "Neural User",
                    session_id: sessionId,
                    vertical_id: verticalId,
                    empresa_config: tenantData
                })
            });
        } catch (e) {
            console.error(e);
        }
    };

    const resetSession = async () => {
        const newId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        try {
            const isBrowser = typeof window !== 'undefined';
            const protocol = isBrowser ? window.location.protocol : 'http:';

            let API_BASE = "";
            if (process.env.NEXT_PUBLIC_API_URL) {
                API_BASE = process.env.NEXT_PUBLIC_API_URL;
            } else {
                API_BASE = `${protocol}//${DEFAULT_API_HOST}`;
            }

            // Limpiar memoria de sesión actual en backend
            if (sessionId) {
                await fetch(`${API_BASE}/test/memory/${sessionId}`, {
                    method: "DELETE"
                });
            }

            // Establecer nueva sesión
            if (isBrowser) {
                localStorage.setItem('nova_session_id', newId);
            }
            setSessionId(newId);

            // Limpiar estado local (sin recargar página)
            setMessages([]);
            setExecutions({});
            setActiveExecutionId(null);
            setRecentLogs([]);
            setHistoryLoaded(true);
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <DashboardContext.Provider
            value={{
                isConnected,
                historyLoaded,
                executions,
                activeExecutionId,
                setActiveExecutionId,
                recentLogs,
                messages,
                sendMessage,
                resetSession,
                graphData,
                modalExecution,
                setModalExecution,
                verticalId,
                setVerticalId,
                tenantData,
                setTenantData,
                sessionId,
            }}
        >
            {children}
        </DashboardContext.Provider>
    );
};
