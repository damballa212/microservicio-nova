
"use client";

import React from "react";
import { Settings, Store, Eye, Laptop, ChevronDown } from "lucide-react";
import { useDashboard } from "../providers/DashboardProvider";
import { cn } from "@/lib/utils";

const VERTICAL_PRESETS = {
    restaurante: {
        nombre: "Pizzeria Don Mario",
        giro: "Pizzeria Artesanal",
        tono: "Alegre y servicial",
        ubicacion: "Av. Caracas Local 4",
        horarios: "12pm - 11pm",
        reglas_reserva: "Reserva via Link",
        delivery_info: "Radio 5km",
        metodos_pago: "Zelle, Efectivo",
        oferta: "Pizza Margarita, Pepperoni",
        reglas: "No mascotas"
    },
    optica: {
        nombre: "Óptica Visión Elite",
        giro: "Salud Visual Premium",
        tono: "Profesional y empático",
        ubicacion: "Centro Comercial Sambil",
        horarios: "9am - 6pm",
        reglas_reserva: "Citas cada 30min",
        delivery_info: "Envios nacionales",
        metodos_pago: "Paypal, Binance",
        oferta: "Monturas Ray-Ban, Cristales Blue",
        reglas: "Garantía de 1 año"
    },
    ecommerce: {
        nombre: "Gadget Store",
        giro: "Tecnología y Accesorios",
        tono: "Moderno y directo",
        ubicacion: "Tienda Online",
        horarios: "24/7",
        reglas_reserva: "N/A",
        delivery_info: "Envíos en 24h",
        metodos_pago: "Bitcoin, TDC",
        oferta: "iPhone 15, AirPods Pro",
        reglas: "7 días para cambios"
    }
};

export const TestSettings = () => {
    const { verticalId, setVerticalId, tenantData, setTenantData } = useDashboard();
    const [isExpanded, setIsExpanded] = React.useState(false);

    const handlePresetChange = (id: string) => {
        setVerticalId(id);
        setTenantData(VERTICAL_PRESETS[id as keyof typeof VERTICAL_PRESETS]);
    };

    const updateField = (key: string, value: string) => {
        setTenantData({ ...tenantData, [key]: value });
    };

    return (
        <div className="border-b border-slate-800 bg-[#0f172a]/30">
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full h-10 px-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Settings className="w-4 h-4 text-slate-400" />
                    <span className="text-[11px] font-bold text-slate-300 uppercase tracking-widest">Simulator Config</span>
                </div>
                <ChevronDown className={cn("w-4 h-4 text-slate-500 transition-transform", isExpanded && "rotate-180")} />
            </button>

            {isExpanded && (
                <div className="p-4 space-y-4 border-t border-slate-800/50 bg-[#020617]/40 animate-in fade-in slide-in-from-top-2 duration-200">
                    {/* Niche Selector */}
                    <div className="space-y-1.5">
                        <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Business Vertical</label>
                        <div className="grid grid-cols-3 gap-2">
                            {Object.keys(VERTICAL_PRESETS).map((id) => (
                                <button
                                    key={id}
                                    onClick={() => handlePresetChange(id)}
                                    className={cn(
                                        "flex flex-col items-center gap-1.5 p-2 rounded-lg border text-[10px] transition-all",
                                        verticalId === id
                                            ? "bg-indigo-500/10 border-indigo-500/50 text-indigo-400"
                                            : "bg-slate-900/50 border-slate-800 text-slate-500 hover:border-slate-700"
                                    )}
                                >
                                    {id === 'restaurante' && <Store className="w-4 h-4" />}
                                    {id === 'optica' && <Eye className="w-4 h-4" />}
                                    {id === 'ecommerce' && <Laptop className="w-4 h-4" />}
                                    <span className="capitalize">{id}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Operational Data Form */}
                    <div className="space-y-3 pt-2">
                        <div className="flex items-center justify-between">
                            <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Operational Data</label>
                            <div className="flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_4px_rgba(16,185,129,0.5)]" />
                                <span className="text-[9px] text-emerald-500/80 font-mono">LIVE SYNC</span>
                            </div>
                        </div>

                        <div className="grid gap-2">
                            {/* Key Fields */}
                            <div className="space-y-1 text-slate-400">
                                <span className="text-[9px] font-mono">NAME_CO</span>
                                <input
                                    value={tenantData.nombre || ""}
                                    onChange={(e) => updateField("nombre", e.target.value)}
                                    className="w-full bg-slate-900/80 border border-slate-800 rounded px-2 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500/30"
                                />
                            </div>
                            <div className="space-y-1 text-slate-400">
                                <span className="text-[9px] font-mono">HORARIOS_INFO</span>
                                <input
                                    value={tenantData.horarios || ""}
                                    onChange={(e) => updateField("horarios", e.target.value)}
                                    className="w-full bg-slate-900/80 border border-slate-800 rounded px-2 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500/30"
                                />
                            </div>
                            <div className="space-y-1 text-slate-400">
                                <span className="text-[9px] font-mono">OFERTA_CATALOGO</span>
                                <textarea
                                    value={tenantData.oferta || ""}
                                    onChange={(e) => updateField("oferta", e.target.value)}
                                    rows={2}
                                    className="w-full bg-slate-900/80 border border-slate-800 rounded px-2 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500/30 resize-none"
                                />
                            </div>
                            <div className="space-y-1 text-slate-400">
                                <span className="text-[9px] font-mono">GOOGLE_SHEET_ID (Inventory)</span>
                                <div className="relative">
                                    <input
                                        value={tenantData.google_sheet_id || ""}
                                        onChange={(e) => updateField("google_sheet_id", e.target.value)}
                                        placeholder="Spreadsheet ID from URL"
                                        className="w-full bg-emerald-900/10 border border-emerald-500/20 rounded px-2 py-1.5 text-[11px] text-emerald-200 placeholder:text-emerald-500/30 focus:outline-none focus:border-emerald-500/50"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="pt-2">
                        <div className="p-2 rounded bg-indigo-500/5 border border-indigo-500/10">
                            <p className="text-[9px] text-indigo-400/80 leading-relaxed">
                                <strong className="text-indigo-300">INFO:</strong> All changes are injected in real-time into the <strong>AI System Prompt</strong>. Send a message to test the updated persona.
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
