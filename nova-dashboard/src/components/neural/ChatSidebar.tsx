
"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, Sparkles } from "lucide-react";
import { useDashboard } from "../providers/DashboardProvider";
import { cn } from "@/lib/utils";
import { TestSettings } from "./TestSettings";

// Reusing the same logic, but un-floating the styles
export const ChatSidebar = () => {
    const { messages = [], sendMessage, isConnected, historyLoaded, sessionId } = useDashboard();
    const [input, setInput] = useState("");
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = () => {
        if (!input.trim() || !isConnected) return;
        sendMessage(input);
        setInput("");
    };

    return (
        <div className="flex flex-col h-full bg-[#020617]/50 backdrop-blur-md">
            {/* Header */}
            <div className="h-14 border-b border-slate-800 flex items-center px-4 bg-[#0f172a]/80">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
                        <Bot className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                        <h2 className="text-sm font-semibold text-slate-100">NOVA Chat</h2>
                        <div className="flex items-center gap-1.5">
                            <span className={cn(
                                "w-2 h-2 rounded-full",
                                isConnected ? (historyLoaded ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-yellow-500 animate-pulse") : "bg-red-500 animate-pulse"
                            )} />
                            <span className="text-[10px] text-slate-400 font-mono uppercase">{isConnected ? (historyLoaded ? "ONLINE" : "LOADING") : "OFFLINE"}</span>
                            {sessionId && (
                                <span className="text-[8px] text-slate-600 font-mono ml-1">
                                    #{sessionId.slice(-8)}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* NEW: Simulator Settings */}
            <TestSettings />

            {/* Messages */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent"
            >
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-slate-500 opacity-60">
                        <Sparkles className="w-8 h-8 mb-2" />
                        <p className="text-xs">System Ready.</p>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div
                        key={i}
                        className={cn(
                            "flex w-full mb-4",
                            msg.role === "user" ? "justify-end" : "justify-start"
                        )}
                    >
                        <div
                            className={cn(
                                "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-lg",
                                msg.role === "user"
                                    ? "bg-indigo-600 text-white rounded-br-none"
                                    : "bg-slate-800/80 text-slate-200 border border-slate-700 rounded-bl-none backdrop-blur-sm"
                            )}
                        >
                            {msg.content}
                        </div>
                    </div>
                ))}
            </div>

            {/* Input */}
            <div className="p-4 border-t border-slate-800 bg-[#0f172a]/50">
                <div className="relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        placeholder="Transmit message..."
                        disabled={!isConnected || !historyLoaded}
                        className="w-full bg-slate-900/50 border border-slate-700 text-slate-200 text-sm rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-all placeholder:text-slate-600"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || !isConnected || !historyLoaded}
                        className="absolute right-2 top-2 p-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:hover:bg-indigo-600"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
};
