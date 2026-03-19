"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useEffect, useState, useCallback } from "react";
import {
    Cpu,
    Key,
    Settings2,
    Thermometer,
    Hash,
    Loader2,
    Check,
    ArrowLeft,
    Search,
    Sparkles,
    RefreshCw,
    CheckCircle2,
    Brain,
    Activity,
    Gauge,
    ChevronRight,
    Edit3,
    Zap,
} from "lucide-react";
import {
    PROVIDERS,
    getModelsByProvider,
    getModelDisplayName,
    type Provider
} from "@/lib/settings-constants";
import { cn } from "@/lib/utils";
import { CredentialsManager } from "@/components/admin/CredentialsManager";
import { API_ENDPOINTS } from "@/lib/api-config";

interface SystemConfig {
    key: string;
    value: string;
    description?: string;
}

type SettingsSection = "ai" | "credentials";

export default function SettingsPage() {
    const [configs, setConfigs] = useState<SystemConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState<string | null>(null);
    const [activeSection, setActiveSection] = useState<SettingsSection>("ai");

    // Model modal state
    const [openModelModal, setOpenModelModal] = useState(false);
    const [modelTargetKey, setModelTargetKey] = useState<string>("llm_model");
    const [modelTargetLabel, setModelTargetLabel] = useState<string>("Main Chat Model");
    const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
    const [searchQuery, setSearchQuery] = useState("");

    // Temperature modal
    const [openTempModal, setOpenTempModal] = useState(false);
    const [tempValue, setTempValue] = useState(0.7);

    // Max Tokens modal
    const [openTokensModal, setOpenTokensModal] = useState(false);
    const [tokensValue, setTokensValue] = useState(4096);

    useEffect(() => { fetchConfigs(); }, []);

    const fetchConfigs = async () => {
        try {
            const res = await fetch(API_ENDPOINTS.CONFIG);
            if (res.ok) {
                const data = await res.json();
                setConfigs(data);
                const tempConfig = data.find((c: SystemConfig) => c.key === "llm_temperature");
                if (tempConfig) setTempValue(parseFloat(tempConfig.value));
                const tokensConfig = data.find((c: SystemConfig) => c.key === "max_tokens");
                if (tokensConfig) setTokensValue(parseInt(tokensConfig.value));
            }
        } catch (error) {
            console.error("Failed to fetch configs", error);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdate = async (key: string, value: string) => {
        setSaving(key);
        try {
            await fetch(`${API_ENDPOINTS.CONFIG}/${key}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ value }),
            });
            // Upsert en local state: actualiza si ya existe, agrega si no
            setConfigs(prev => {
                const exists = prev.some(c => c.key === key);
                if (exists) return prev.map(c => c.key === key ? { ...c, value } : c);
                return [...prev, { key, value }];
            });
        } catch (error) {
            console.error("Failed to save config", error);
        } finally {
            setSaving(null);
        }
    };

    const openModelPicker = (key: string, label: string) => {
        setModelTargetKey(key);
        setModelTargetLabel(label);
        setSelectedProvider(null);
        setSearchQuery("");
        setOpenModelModal(true);
    };

    const handleModelSelect = async (modelId: string) => {
        await handleUpdate(modelTargetKey, modelId);
        setOpenModelModal(false);
    };

    const handleTempSave = async () => {
        await handleUpdate("llm_temperature", tempValue.toString());
        setOpenTempModal(false);
    };

    const handleTokensSave = async () => {
        await handleUpdate("max_tokens", tokensValue.toString());
        setOpenTokensModal(false);
    };

    const getConfigValue = (key: string) => configs.find(c => c.key === key)?.value || "";

    const getFilteredModels = () => {
        if (!selectedProvider) return [];
        const models = getModelsByProvider(selectedProvider.id);
        if (!searchQuery) return models;
        return models.filter(m =>
            m.toLowerCase().includes(searchQuery.toLowerCase()) ||
            getModelDisplayName(m).toLowerCase().includes(searchQuery.toLowerCase())
        );
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-4">
                    <div className="relative">
                        <div className="w-16 h-16 rounded-full border-4 border-slate-800 border-t-indigo-500 animate-spin" />
                        <Sparkles className="absolute inset-0 m-auto w-6 h-6 text-indigo-400" />
                    </div>
                    <p className="text-slate-400">Loading settings...</p>
                </div>
            </div>
        );
    }

    const currentModel = getConfigValue("llm_model");
    const currentClassifier = getConfigValue("classifier_model");
    const currentEmbeddings = getConfigValue("embeddings_model");
    const currentTemp = parseFloat(getConfigValue("llm_temperature") || "0.7");
    const currentTokens = parseInt(getConfigValue("max_tokens") || "4096");

    const modelRows = [
        {
            key: "llm_model",
            label: "Main Chat",
            description: "Handles all conversation responses",
            icon: <Brain className="w-4 h-4" />,
            color: "bg-indigo-500/10 text-indigo-400",
            value: currentModel,
        },
        {
            key: "classifier_model",
            label: "Intent Classifier",
            description: "Detects user intent & lead scoring",
            icon: <Activity className="w-4 h-4" />,
            color: "bg-purple-500/10 text-purple-400",
            value: currentClassifier || currentModel,
            badge: !currentClassifier ? "Using main" : undefined,
        },
        {
            key: "embeddings_model",
            label: "Embeddings",
            description: "Semantic memory & RAG",
            icon: <Gauge className="w-4 h-4" />,
            color: "bg-cyan-500/10 text-cyan-400",
            value: currentEmbeddings || "text-embedding-3-small",
            badge: !currentEmbeddings ? "Default" : undefined,
        },
    ];

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="shrink-0 px-8 pt-6 pb-4 border-b border-slate-800/50">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                            <div className="p-2 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600">
                                <Settings2 className="w-5 h-5 text-white" />
                            </div>
                            System Settings
                        </h1>
                        <p className="text-slate-400 mt-1 ml-12">Configure AI behavior and manage API credentials</p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={fetchConfigs} className="text-slate-400 hover:text-white">
                        <RefreshCw className="w-4 h-4 mr-2" />Refresh
                    </Button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex-1 overflow-hidden">
                <Tabs value={activeSection} onValueChange={(v) => setActiveSection(v as SettingsSection)} className="h-full flex flex-col">
                    <div className="shrink-0 px-8 pt-4 bg-slate-950/50">
                        <TabsList className="bg-slate-900/50 border border-slate-800 p-1">
                            <TabsTrigger value="ai" className="text-slate-400 data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-2 px-6">
                                <Brain className="w-4 h-4" />AI Configuration
                            </TabsTrigger>
                            <TabsTrigger value="credentials" className="text-slate-400 data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-2 px-6">
                                <Key className="w-4 h-4" />API Credentials
                            </TabsTrigger>
                        </TabsList>
                    </div>

                    <div className="flex-1 overflow-y-auto px-8 py-6">
                        {/* AI Configuration Tab */}
                        <TabsContent value="ai" className="mt-0 space-y-5">

                            {/* Models Section */}
                            <Card className="bg-slate-900/50 border-slate-800">
                                <CardHeader className="pb-3">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <CardTitle className="text-white flex items-center gap-2">
                                                <Zap className="w-5 h-5 text-indigo-400" />
                                                AI Models
                                            </CardTitle>
                                            <CardDescription className="text-slate-400 mt-1">
                                                300+ models via OpenRouter — configure each agent independently
                                            </CardDescription>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-2">
                                    {modelRows.map((row) => (
                                        <div
                                            key={row.key}
                                            className="flex items-center gap-4 p-4 rounded-xl bg-slate-800/50 border border-slate-700/30 hover:border-slate-600/50 transition-colors group"
                                        >
                                            <div className={cn("p-2.5 rounded-xl shrink-0", row.color)}>
                                                {row.icon}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <p className="text-sm font-semibold text-white">{row.label}</p>
                                                    {row.badge && (
                                                        <Badge className="bg-slate-700 text-slate-400 border-0 text-[10px] h-4 px-1.5">
                                                            {row.badge}
                                                        </Badge>
                                                    )}
                                                    {!row.badge && (
                                                        <Badge className="bg-emerald-500/15 text-emerald-400 border-0 text-[10px] h-4 px-1.5">
                                                            <CheckCircle2 className="w-2.5 h-2.5 mr-1" />Active
                                                        </Badge>
                                                    )}
                                                </div>
                                                <p className="text-xs text-slate-500 mt-0.5">{row.description}</p>
                                                <p className="text-xs text-slate-400 font-mono mt-1 truncate">{row.value || "Not configured"}</p>
                                            </div>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => openModelPicker(row.key, row.label)}
                                                className="shrink-0 border-slate-700 hover:bg-indigo-600 hover:border-indigo-600 hover:text-white transition-all"
                                            >
                                                <Edit3 className="w-3 h-3 mr-1" />Change
                                            </Button>
                                        </div>
                                    ))}
                                </CardContent>
                            </Card>

                            {/* Parameters */}
                            <div className="grid grid-cols-2 gap-5">
                                {/* Temperature */}
                                <Card className="bg-slate-900/50 border-slate-800">
                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-white text-base flex items-center gap-2">
                                            <Thermometer className="w-4 h-4 text-amber-400" />
                                            Temperature
                                        </CardTitle>
                                        <CardDescription className="text-slate-400 text-sm">Controls response randomness</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <span className="text-3xl font-bold text-white">{currentTemp.toFixed(2)}</span>
                                                <Button size="sm" variant="outline"
                                                    onClick={() => { setTempValue(currentTemp); setOpenTempModal(true); }}
                                                    className="border-slate-700 hover:bg-slate-800">
                                                    <Edit3 className="w-3 h-3 mr-1" />Adjust
                                                </Button>
                                            </div>
                                            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                                <div className="h-full bg-gradient-to-r from-blue-500 via-amber-500 to-red-500 transition-all"
                                                    style={{ width: `${currentTemp * 100}%` }} />
                                            </div>
                                            <div className="flex justify-between text-xs text-slate-500">
                                                <span>Precise</span><span>Balanced</span><span>Creative</span>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>

                                {/* Max Tokens */}
                                <Card className="bg-slate-900/50 border-slate-800">
                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-white text-base flex items-center gap-2">
                                            <Hash className="w-4 h-4 text-emerald-400" />
                                            Max Tokens
                                        </CardTitle>
                                        <CardDescription className="text-slate-400 text-sm">Maximum response length</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <span className="text-3xl font-bold text-white">{currentTokens.toLocaleString()}</span>
                                                <Button size="sm" variant="outline"
                                                    onClick={() => { setTokensValue(currentTokens); setOpenTokensModal(true); }}
                                                    className="border-slate-700 hover:bg-slate-800">
                                                    <Edit3 className="w-3 h-3 mr-1" />Adjust
                                                </Button>
                                            </div>
                                            <div className="grid grid-cols-4 gap-2">
                                                {[1024, 2048, 4096, 8192].map((val) => (
                                                    <button key={val}
                                                        onClick={() => handleUpdate("max_tokens", val.toString())}
                                                        className={cn(
                                                            "py-2 px-3 rounded-lg text-sm font-medium transition-all border",
                                                            currentTokens === val
                                                                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                                                                : "bg-slate-800 text-slate-400 hover:bg-slate-700 border-transparent"
                                                        )}>
                                                        {val >= 1000 ? `${val / 1000}K` : val}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        </TabsContent>

                        {/* Credentials Tab */}
                        <TabsContent value="credentials" className="mt-0">
                            <CredentialsManager />
                        </TabsContent>
                    </div>
                </Tabs>
            </div>

            {/* MODEL SELECTION MODAL */}
            <Dialog open={openModelModal} onOpenChange={(open) => {
                if (!open) { setSelectedProvider(null); setSearchQuery(""); }
                setOpenModelModal(open);
            }}>
                <DialogContent className="sm:max-w-[800px] bg-slate-950 border-slate-800 text-white p-0 overflow-hidden h-[650px] max-h-[90vh]">
                    <DialogHeader className="px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                        <div className="flex items-center gap-3">
                            {selectedProvider && (
                                <Button variant="ghost" size="icon"
                                    onClick={() => { setSelectedProvider(null); setSearchQuery(""); }}
                                    className="h-8 w-8 text-slate-400 hover:text-white">
                                    <ArrowLeft className="h-4 w-4" />
                                </Button>
                            )}
                            <div>
                                <DialogTitle className="text-lg">
                                    {selectedProvider
                                        ? `${selectedProvider.icon} ${selectedProvider.name} Models`
                                        : `Select model — ${modelTargetLabel}`}
                                </DialogTitle>
                                <DialogDescription className="text-slate-400">
                                    {selectedProvider
                                        ? `${getModelsByProvider(selectedProvider.id).length} models available`
                                        : "Choose a provider to see available models"}
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>

                    {/* Provider Grid */}
                    {!selectedProvider && (
                        <div className="flex-1 overflow-y-auto p-6">
                            <div className="grid grid-cols-3 gap-4">
                                {PROVIDERS.map((provider) => {
                                    const modelCount = getModelsByProvider(provider.id).length;
                                    return (
                                        <button key={provider.id} onClick={() => setSelectedProvider(provider)}
                                            className="group relative p-6 rounded-xl border border-slate-800 transition-all duration-200 hover:border-slate-600 hover:bg-slate-900/80 hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-indigo-500/50">
                                            <div className={cn("absolute inset-0 rounded-xl opacity-0 group-hover:opacity-10 transition-opacity bg-gradient-to-br", provider.color)} />
                                            <div className="relative flex flex-col items-center text-center gap-3">
                                                <span className="text-4xl">{provider.icon}</span>
                                                <div>
                                                    <h3 className="font-semibold text-slate-200 group-hover:text-white">{provider.name}</h3>
                                                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{provider.description}</p>
                                                </div>
                                                <Badge variant="secondary" className="bg-slate-800 text-slate-400 text-xs">
                                                    {modelCount} models
                                                </Badge>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Model List */}
                    {selectedProvider && (
                        <div className="flex-1 flex flex-col overflow-hidden">
                            <div className="px-6 py-3 border-b border-slate-800/50">
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                                    <Input placeholder={`Search ${selectedProvider.name} models...`}
                                        value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                                        className="pl-10 bg-slate-900 border-slate-700 text-slate-200 placeholder:text-slate-500"
                                        autoFocus />
                                </div>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4">
                                <div className="space-y-1">
                                    {getFilteredModels().length === 0 ? (
                                        <div className="py-12 text-center text-slate-500">
                                            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                            <p>No models found matching "{searchQuery}"</p>
                                        </div>
                                    ) : (
                                        getFilteredModels().map((modelId) => {
                                            const currentVal = getConfigValue(modelTargetKey);
                                            const isSelected = currentVal === modelId;
                                            return (
                                                <button key={modelId} onClick={() => handleModelSelect(modelId)}
                                                    className={cn(
                                                        "w-full flex items-center gap-3 p-3 rounded-lg transition-all text-left hover:bg-slate-800/60 border border-transparent",
                                                        isSelected && "bg-indigo-500/10 border-indigo-500/30"
                                                    )}>
                                                    <div className={cn("w-5 h-5 rounded-full border flex items-center justify-center shrink-0",
                                                        isSelected ? "bg-emerald-500 border-emerald-500 text-black" : "border-slate-600")}>
                                                        {isSelected && <Check className="w-3 h-3" />}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <span className={cn("font-medium truncate", isSelected ? "text-white" : "text-slate-300")}>
                                                                {getModelDisplayName(modelId)}
                                                            </span>
                                                            {modelId.includes(':free') && (
                                                                <Badge className="bg-green-500/20 text-green-400 text-[9px] h-4 px-1 border-0">FREE</Badge>
                                                            )}
                                                        </div>
                                                        <span className="text-xs text-slate-500 font-mono block truncate">{modelId}</span>
                                                    </div>
                                                    {saving === modelTargetKey && isSelected && (
                                                        <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                                                    )}
                                                </button>
                                            );
                                        })
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* TEMPERATURE MODAL */}
            <Dialog open={openTempModal} onOpenChange={setOpenTempModal}>
                <DialogContent className="sm:max-w-[450px] bg-slate-950 border-slate-800 text-white">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Thermometer className="w-5 h-5 text-amber-400" />Adjust Temperature
                        </DialogTitle>
                        <DialogDescription className="text-slate-400">
                            Lower values = more focused. Higher values = more creative.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-6 space-y-6">
                        <div className="text-center">
                            <span className="text-5xl font-bold text-white">{tempValue.toFixed(2)}</span>
                        </div>
                        <Slider value={[tempValue]} onValueChange={([v]) => setTempValue(v)} min={0} max={1} step={0.01} className="w-full" />
                        <div className="flex justify-between text-sm gap-2">
                            {[{ label: "Precise (0.0)", v: 0, color: "bg-blue-500/20 text-blue-400 hover:bg-blue-500/30" },
                              { label: "Balanced (0.5)", v: 0.5, color: "bg-amber-500/20 text-amber-400 hover:bg-amber-500/30" },
                              { label: "Creative (1.0)", v: 1.0, color: "bg-red-500/20 text-red-400 hover:bg-red-500/30" }
                            ].map(o => (
                                <button key={o.v} onClick={() => setTempValue(o.v)}
                                    className={cn("flex-1 py-1.5 rounded-lg transition-colors text-xs", o.color)}>{o.label}</button>
                            ))}
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setOpenTempModal(false)}>Cancel</Button>
                        <Button onClick={handleTempSave} className="bg-indigo-600 hover:bg-indigo-700" disabled={saving === "llm_temperature"}>
                            {saving === "llm_temperature" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Check className="w-4 h-4 mr-2" />}
                            Save
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* MAX TOKENS MODAL */}
            <Dialog open={openTokensModal} onOpenChange={setOpenTokensModal}>
                <DialogContent className="sm:max-w-[450px] bg-slate-950 border-slate-800 text-white">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Hash className="w-5 h-5 text-emerald-400" />Set Max Tokens
                        </DialogTitle>
                        <DialogDescription className="text-slate-400">
                            Maximum number of tokens in AI responses.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-6 space-y-6">
                        <div className="text-center">
                            <span className="text-5xl font-bold text-white">{tokensValue.toLocaleString()}</span>
                            <p className="text-sm text-slate-500 mt-1">tokens</p>
                        </div>
                        <Input type="number" value={tokensValue}
                            onChange={(e) => setTokensValue(parseInt(e.target.value) || 0)}
                            min={256} max={128000} step={256}
                            className="text-center text-lg bg-slate-900 border-slate-700" />
                        <div className="grid grid-cols-4 gap-2">
                            {[1024, 2048, 4096, 8192, 16384, 32768, 65536, 128000].map((val) => (
                                <button key={val} onClick={() => setTokensValue(val)}
                                    className={cn("py-2 px-3 rounded-lg text-sm font-medium transition-all border",
                                        tokensValue === val
                                            ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                                            : "bg-slate-800 text-slate-400 hover:bg-slate-700 border-transparent")}>
                                    {val >= 1000 ? `${val / 1000}K` : val}
                                </button>
                            ))}
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setOpenTokensModal(false)}>Cancel</Button>
                        <Button onClick={handleTokensSave} className="bg-indigo-600 hover:bg-indigo-700" disabled={saving === "max_tokens"}>
                            {saving === "max_tokens" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Check className="w-4 h-4 mr-2" />}
                            Save
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
