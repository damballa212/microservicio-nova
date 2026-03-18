"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
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
    ChevronsUpDown,
    ArrowLeft,
    Search,
    Sparkles,
    Zap,
    Shield,
    Activity,
    ChevronRight,
    Edit3,
    RefreshCw,
    CheckCircle2,
    Brain,
    Gauge
} from "lucide-react";
import {
    SETTINGS_LABELS,
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

    // Model Selection Modal
    const [openModelModal, setOpenModelModal] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
    const [searchQuery, setSearchQuery] = useState("");

    // Temperature Modal
    const [openTempModal, setOpenTempModal] = useState(false);
    const [tempValue, setTempValue] = useState(0.7);

    // Max Tokens Modal
    const [openTokensModal, setOpenTokensModal] = useState(false);
    const [tokensValue, setTokensValue] = useState(4096);

    useEffect(() => {
        fetchConfigs();
    }, []);

    const fetchConfigs = async () => {
        try {
            const res = await fetch(API_ENDPOINTS.CONFIG);
            if (res.ok) {
                const data = await res.json();
                setConfigs(data);
                // Initialize local values
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
            setConfigs(prev => prev.map(c => c.key === key ? { ...c, value } : c));
        } catch (error) {
            console.error("Failed to save config", error);
        } finally {
            setSaving(null);
        }
    };

    const handleModelSelect = async (modelId: string) => {
        await handleUpdate("llm_model", modelId);
        setOpenModelModal(false);
        setSelectedProvider(null);
        setSearchQuery("");
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

    const getCurrentModelInfo = (modelId: string) => ({
        id: modelId,
        name: getModelDisplayName(modelId),
        provider: modelId.split('/')[0] || 'Unknown'
    });

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
    const currentTemp = parseFloat(getConfigValue("llm_temperature") || "0.7");
    const currentTokens = parseInt(getConfigValue("max_tokens") || "4096");

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="shrink-0 px-8 pt-6 pb-4 border-b border-slate-800/50 bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/30">
                <div className="max-w-7xl mx-auto">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                                <div className="p-2 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/20">
                                    <Settings2 className="w-5 h-5 text-white" />
                                </div>
                                System Settings
                            </h1>
                            <p className="text-slate-400 mt-1 ml-12">Configure AI behavior and manage API credentials</p>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={fetchConfigs}
                                className="text-slate-400 hover:text-white"
                            >
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Refresh
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content with Tabs */}
            <div className="flex-1 overflow-hidden">
                <Tabs value={activeSection} onValueChange={(v) => setActiveSection(v as SettingsSection)} className="h-full flex flex-col">
                    {/* Tab Navigation */}
                    <div className="shrink-0 px-8 pt-4 bg-slate-950/50">
                        <div className="max-w-7xl mx-auto">
                            <TabsList className="bg-slate-900/50 border border-slate-800 p-1">
                                <TabsTrigger
                                    value="ai"
                                    className="text-slate-400 data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-2 px-6"
                                >
                                    <Brain className="w-4 h-4" />
                                    AI Configuration
                                </TabsTrigger>
                                <TabsTrigger
                                    value="credentials"
                                    className="text-slate-400 data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-2 px-6"
                                >
                                    <Key className="w-4 h-4" />
                                    API Credentials
                                </TabsTrigger>
                            </TabsList>
                        </div>
                    </div>

                    {/* Tab Content */}
                    <div className="flex-1 overflow-y-auto px-8 py-6">
                        <div className="max-w-7xl mx-auto">
                            {/* AI Configuration Tab */}
                            <TabsContent value="ai" className="mt-0 space-y-6">
                                {/* Quick Stats Row */}
                                <div className="grid grid-cols-3 gap-4">
                                    <Card
                                        className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700/50 cursor-pointer hover:border-indigo-500/50 transition-all group"
                                        onClick={() => setOpenModelModal(true)}
                                    >
                                        <CardContent className="p-5">
                                            <div className="flex items-start justify-between">
                                                <div className="flex-1">
                                                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Model</p>
                                                    <p className="text-lg font-semibold text-white mt-1 truncate">
                                                        {currentModel ? getCurrentModelInfo(currentModel).name : "Not Selected"}
                                                    </p>
                                                    <p className="text-xs text-slate-500 font-mono mt-0.5 truncate">
                                                        {currentModel || "Click to select"}
                                                    </p>
                                                </div>
                                                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition-all">
                                                    <Cpu className="w-5 h-5" />
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    <Card
                                        className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700/50 cursor-pointer hover:border-amber-500/50 transition-all group"
                                        onClick={() => {
                                            setTempValue(currentTemp);
                                            setOpenTempModal(true);
                                        }}
                                    >
                                        <CardContent className="p-5">
                                            <div className="flex items-start justify-between">
                                                <div className="flex-1">
                                                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Temperature</p>
                                                    <p className="text-3xl font-bold text-white mt-1">
                                                        {currentTemp.toFixed(2)}
                                                    </p>
                                                    <p className="text-xs text-slate-500 mt-0.5">
                                                        {currentTemp < 0.3 ? "Precise" : currentTemp < 0.7 ? "Balanced" : "Creative"}
                                                    </p>
                                                </div>
                                                <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 group-hover:bg-amber-500 group-hover:text-white transition-all">
                                                    <Thermometer className="w-5 h-5" />
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    <Card
                                        className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700/50 cursor-pointer hover:border-emerald-500/50 transition-all group"
                                        onClick={() => {
                                            setTokensValue(currentTokens);
                                            setOpenTokensModal(true);
                                        }}
                                    >
                                        <CardContent className="p-5">
                                            <div className="flex items-start justify-between">
                                                <div className="flex-1">
                                                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Max Tokens</p>
                                                    <p className="text-3xl font-bold text-white mt-1">
                                                        {currentTokens.toLocaleString()}
                                                    </p>
                                                    <p className="text-xs text-slate-500 mt-0.5">
                                                        Response limit
                                                    </p>
                                                </div>
                                                <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition-all">
                                                    <Hash className="w-5 h-5" />
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                </div>

                                {/* Model Selection Card */}
                                <Card className="bg-slate-900/50 border-slate-800">
                                    <CardHeader className="pb-4">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <CardTitle className="text-white flex items-center gap-2">
                                                    <Sparkles className="w-5 h-5 text-indigo-400" />
                                                    AI Model Selection
                                                </CardTitle>
                                                <CardDescription className="text-slate-400 mt-1">
                                                    Choose from 300+ models across multiple providers via OpenRouter
                                                </CardDescription>
                                            </div>
                                            <Button
                                                onClick={() => setOpenModelModal(true)}
                                                className="bg-indigo-600 hover:bg-indigo-700"
                                            >
                                                <Edit3 className="w-4 h-4 mr-2" />
                                                Change Model
                                            </Button>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        {currentModel ? (
                                            <div className="flex items-center gap-4 p-4 rounded-xl bg-slate-800/50 border border-slate-700/50">
                                                <div className="p-3 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600">
                                                    <Cpu className="w-6 h-6 text-white" />
                                                </div>
                                                <div className="flex-1">
                                                    <p className="font-semibold text-white text-lg">{getCurrentModelInfo(currentModel).name}</p>
                                                    <p className="text-sm text-slate-400 font-mono">{currentModel}</p>
                                                </div>
                                                <Badge className="bg-emerald-500/20 text-emerald-400 border-0">
                                                    <CheckCircle2 className="w-3 h-3 mr-1" />
                                                    Active
                                                </Badge>
                                            </div>
                                        ) : (
                                            <div className="text-center py-8 text-slate-500">
                                                <Cpu className="w-10 h-10 mx-auto mb-3 opacity-30" />
                                                <p>No model selected. Click "Change Model" to get started.</p>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>

                                {/* Parameters Grid */}
                                <div className="grid grid-cols-2 gap-6">
                                    {/* Temperature Card */}
                                    <Card className="bg-slate-900/50 border-slate-800">
                                        <CardHeader className="pb-3">
                                            <CardTitle className="text-white text-base flex items-center gap-2">
                                                <Thermometer className="w-4 h-4 text-amber-400" />
                                                Temperature
                                            </CardTitle>
                                            <CardDescription className="text-slate-400 text-sm">
                                                Controls randomness in responses
                                            </CardDescription>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-4">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-3xl font-bold text-white">{currentTemp.toFixed(2)}</span>
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={() => {
                                                            setTempValue(currentTemp);
                                                            setOpenTempModal(true);
                                                        }}
                                                        className="border-slate-700 hover:bg-slate-800"
                                                    >
                                                        <Edit3 className="w-3 h-3 mr-1" />
                                                        Adjust
                                                    </Button>
                                                </div>
                                                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-blue-500 via-amber-500 to-red-500 transition-all"
                                                        style={{ width: `${currentTemp * 100}%` }}
                                                    />
                                                </div>
                                                <div className="flex justify-between text-xs text-slate-500">
                                                    <span>Precise</span>
                                                    <span>Balanced</span>
                                                    <span>Creative</span>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    {/* Max Tokens Card */}
                                    <Card className="bg-slate-900/50 border-slate-800">
                                        <CardHeader className="pb-3">
                                            <CardTitle className="text-white text-base flex items-center gap-2">
                                                <Hash className="w-4 h-4 text-emerald-400" />
                                                Max Tokens
                                            </CardTitle>
                                            <CardDescription className="text-slate-400 text-sm">
                                                Maximum response length
                                            </CardDescription>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-4">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-3xl font-bold text-white">{currentTokens.toLocaleString()}</span>
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={() => {
                                                            setTokensValue(currentTokens);
                                                            setOpenTokensModal(true);
                                                        }}
                                                        className="border-slate-700 hover:bg-slate-800"
                                                    >
                                                        <Edit3 className="w-3 h-3 mr-1" />
                                                        Adjust
                                                    </Button>
                                                </div>
                                                <div className="grid grid-cols-4 gap-2">
                                                    {[1024, 2048, 4096, 8192].map((val) => (
                                                        <button
                                                            key={val}
                                                            onClick={() => handleUpdate("max_tokens", val.toString())}
                                                            className={cn(
                                                                "py-2 px-3 rounded-lg text-sm font-medium transition-all",
                                                                currentTokens === val
                                                                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                                                    : "bg-slate-800 text-slate-400 hover:bg-slate-700 border border-transparent"
                                                            )}
                                                        >
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
                    </div>
                </Tabs>
            </div>

            {/* MODEL SELECTION MODAL */}
            <Dialog open={openModelModal} onOpenChange={(open) => {
                setOpenModelModal(open);
                if (!open) {
                    setSelectedProvider(null);
                    setSearchQuery("");
                }
            }}>
                <DialogContent className="sm:max-w-[800px] bg-slate-950 border-slate-800 text-white p-0 overflow-hidden h-[650px] max-h-[90vh]">
                    <DialogHeader className="px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                        <div className="flex items-center gap-3">
                            {selectedProvider && (
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => {
                                        setSelectedProvider(null);
                                        setSearchQuery("");
                                    }}
                                    className="h-8 w-8 text-slate-400 hover:text-white"
                                >
                                    <ArrowLeft className="h-4 w-4" />
                                </Button>
                            )}
                            <div>
                                <DialogTitle className="text-lg">
                                    {selectedProvider
                                        ? `${selectedProvider.icon} ${selectedProvider.name} Models`
                                        : "Select AI Provider"
                                    }
                                </DialogTitle>
                                <DialogDescription className="text-slate-400">
                                    {selectedProvider
                                        ? `${getModelsByProvider(selectedProvider.id).length} models available`
                                        : "Choose a provider to see available models"
                                    }
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
                                        <button
                                            key={provider.id}
                                            onClick={() => setSelectedProvider(provider)}
                                            className={cn(
                                                "group relative p-6 rounded-xl border border-slate-800 transition-all duration-200",
                                                "hover:border-slate-600 hover:bg-slate-900/80 hover:shadow-xl hover:-translate-y-1",
                                                "focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                                            )}
                                        >
                                            <div className={cn(
                                                "absolute inset-0 rounded-xl opacity-0 group-hover:opacity-10 transition-opacity bg-gradient-to-br",
                                                provider.color
                                            )} />
                                            <div className="relative flex flex-col items-center text-center gap-3">
                                                <span className="text-4xl">{provider.icon}</span>
                                                <div>
                                                    <h3 className="font-semibold text-slate-200 group-hover:text-white transition-colors">
                                                        {provider.name}
                                                    </h3>
                                                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                                                        {provider.description}
                                                    </p>
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
                                    <Input
                                        placeholder={`Search ${selectedProvider.name} models...`}
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="pl-10 bg-slate-900 border-slate-700 text-slate-200 placeholder:text-slate-500"
                                        autoFocus
                                    />
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
                                            const isSelected = currentModel === modelId;
                                            const isFree = modelId.includes(':free');
                                            const isThinking = modelId.includes(':thinking');

                                            return (
                                                <button
                                                    key={modelId}
                                                    onClick={() => handleModelSelect(modelId)}
                                                    className={cn(
                                                        "w-full flex items-center gap-3 p-3 rounded-lg transition-all text-left",
                                                        "hover:bg-slate-800/60 border border-transparent",
                                                        isSelected && "bg-indigo-500/10 border-indigo-500/30"
                                                    )}
                                                >
                                                    <div className={cn(
                                                        "w-5 h-5 rounded-full border flex items-center justify-center shrink-0",
                                                        isSelected
                                                            ? "bg-emerald-500 border-emerald-500 text-black"
                                                            : "border-slate-600"
                                                    )}>
                                                        {isSelected && <Check className="w-3 h-3" />}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <span className={cn(
                                                                "font-medium truncate",
                                                                isSelected ? "text-white" : "text-slate-300"
                                                            )}>
                                                                {getModelDisplayName(modelId)}
                                                            </span>
                                                            {isFree && (
                                                                <Badge className="bg-green-500/20 text-green-400 text-[9px] h-4 px-1 border-0">
                                                                    FREE
                                                                </Badge>
                                                            )}
                                                            {isThinking && (
                                                                <Badge className="bg-purple-500/20 text-purple-400 text-[9px] h-4 px-1 border-0">
                                                                    THINKING
                                                                </Badge>
                                                            )}
                                                        </div>
                                                        <span className="text-xs text-slate-500 font-mono block truncate">
                                                            {modelId}
                                                        </span>
                                                    </div>
                                                    {saving === "llm_model" && isSelected && (
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
                            <Thermometer className="w-5 h-5 text-amber-400" />
                            Adjust Temperature
                        </DialogTitle>
                        <DialogDescription className="text-slate-400">
                            Lower values make responses more focused and deterministic. Higher values increase creativity and randomness.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-6 space-y-6">
                        <div className="text-center">
                            <span className="text-5xl font-bold text-white">{tempValue.toFixed(2)}</span>
                        </div>
                        <Slider
                            value={[tempValue]}
                            onValueChange={([v]) => setTempValue(v)}
                            min={0}
                            max={1}
                            step={0.01}
                            className="w-full"
                        />
                        <div className="flex justify-between text-sm">
                            <button
                                onClick={() => setTempValue(0)}
                                className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors"
                            >
                                Precise (0.0)
                            </button>
                            <button
                                onClick={() => setTempValue(0.5)}
                                className="px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
                            >
                                Balanced (0.5)
                            </button>
                            <button
                                onClick={() => setTempValue(1.0)}
                                className="px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                            >
                                Creative (1.0)
                            </button>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setOpenTempModal(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleTempSave}
                            className="bg-indigo-600 hover:bg-indigo-700"
                            disabled={saving === "llm_temperature"}
                        >
                            {saving === "llm_temperature" ? (
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            ) : (
                                <Check className="w-4 h-4 mr-2" />
                            )}
                            Save Changes
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* MAX TOKENS MODAL */}
            <Dialog open={openTokensModal} onOpenChange={setOpenTokensModal}>
                <DialogContent className="sm:max-w-[450px] bg-slate-950 border-slate-800 text-white">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Hash className="w-5 h-5 text-emerald-400" />
                            Set Max Tokens
                        </DialogTitle>
                        <DialogDescription className="text-slate-400">
                            Define the maximum number of tokens (words/characters) in AI responses.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-6 space-y-6">
                        <div className="text-center">
                            <span className="text-5xl font-bold text-white">{tokensValue.toLocaleString()}</span>
                            <p className="text-sm text-slate-500 mt-1">tokens</p>
                        </div>
                        <Input
                            type="number"
                            value={tokensValue}
                            onChange={(e) => setTokensValue(parseInt(e.target.value) || 0)}
                            min={256}
                            max={128000}
                            step={256}
                            className="text-center text-lg bg-slate-900 border-slate-700"
                        />
                        <div className="grid grid-cols-4 gap-2">
                            {[1024, 2048, 4096, 8192, 16384, 32768, 65536, 128000].map((val) => (
                                <button
                                    key={val}
                                    onClick={() => setTokensValue(val)}
                                    className={cn(
                                        "py-2 px-3 rounded-lg text-sm font-medium transition-all",
                                        tokensValue === val
                                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                            : "bg-slate-800 text-slate-400 hover:bg-slate-700 border border-transparent"
                                    )}
                                >
                                    {val >= 1000 ? `${val / 1000}K` : val}
                                </button>
                            ))}
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setOpenTokensModal(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleTokensSave}
                            className="bg-indigo-600 hover:bg-indigo-700"
                            disabled={saving === "max_tokens"}
                        >
                            {saving === "max_tokens" ? (
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            ) : (
                                <Check className="w-4 h-4 mr-2" />
                            )}
                            Save Changes
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
