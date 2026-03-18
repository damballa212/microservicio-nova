"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogFooter,
    DialogDescription,
} from "@/components/ui/dialog";
import { useEffect, useState } from "react";
import {
    Plus,
    Trash2,
    Check,
    Loader2,
    Star,
    StarOff,
    TestTube,
    CheckCircle2,
    XCircle,
    Edit,
    Key,
    Clock
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_ENDPOINTS } from "@/lib/api-config";

// Provider definitions matching backend
const CREDENTIAL_PROVIDERS = [
    { id: "openrouter", name: "OpenRouter", icon: "🔀", description: "Unified API for 300+ models", color: "from-pink-500 to-rose-500", defaultUrl: "https://openrouter.ai/api/v1" },
    { id: "openai", name: "OpenAI", icon: "🤖", description: "GPT-4, GPT-5, o1, o3 series", color: "from-emerald-500 to-teal-500", defaultUrl: "https://api.openai.com/v1" },
    { id: "anthropic", name: "Anthropic", icon: "🧠", description: "Claude 3.5, 3.7, 4.5 series", color: "from-orange-500 to-amber-500", defaultUrl: "https://api.anthropic.com/v1" },
    { id: "google", name: "Google", icon: "✨", description: "Gemini 2.5, 3.0 series", color: "from-blue-500 to-indigo-500", defaultUrl: "" },
    { id: "cohere", name: "Cohere", icon: "🌊", description: "Command R series", color: "from-purple-500 to-violet-500", defaultUrl: "https://api.cohere.ai/v1" },
    { id: "mistral", name: "Mistral", icon: "🌀", description: "Mistral, Mixtral, Codestral", color: "from-violet-500 to-purple-500", defaultUrl: "https://api.mistral.ai/v1" },
    { id: "other", name: "Other", icon: "🌐", description: "Custom providers", color: "from-slate-500 to-gray-500", defaultUrl: "" },
];

interface Credential {
    id: string;
    provider: string;
    name: string;
    api_key_masked: string;
    base_url?: string;
    is_default: boolean;
    is_active: boolean;
    last_used_at?: string;
    created_at?: string;
}

interface CredentialsManagerProps {
    onCredentialChange?: () => void;
}

export function CredentialsManager({ onCredentialChange }: CredentialsManagerProps) {
    const [credentials, setCredentials] = useState<Credential[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [testingId, setTestingId] = useState<string | null>(null);
    const [testResult, setTestResult] = useState<{ id: string, success: boolean, message: string } | null>(null);
    const [savingId, setSavingId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    // Form state for new credential
    const [newCredential, setNewCredential] = useState({
        provider: "",
        name: "",
        api_key: "",
        base_url: "",
        is_default: true,
    });

    useEffect(() => {
        fetchCredentials();
    }, []);

    const fetchCredentials = async () => {
        try {
            const res = await fetch(API_ENDPOINTS.CREDENTIALS);
            if (res.ok) {
                const data = await res.json();
                setCredentials(data.credentials || []);
            }
        } catch (error) {
            console.error("Failed to fetch credentials", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async () => {
        if (!newCredential.provider || !newCredential.name || !newCredential.api_key) {
            return;
        }

        setSavingId("new");
        try {
            const res = await fetch(API_ENDPOINTS.CREDENTIALS, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    provider: newCredential.provider,
                    name: newCredential.name,
                    api_key: newCredential.api_key,
                    base_url: newCredential.base_url || null,
                    is_default: newCredential.is_default,
                }),
            });

            if (res.ok) {
                await fetchCredentials();
                setShowAddModal(false);
                setNewCredential({ provider: "", name: "", api_key: "", base_url: "", is_default: true });
                onCredentialChange?.();
            }
        } catch (error) {
            console.error("Failed to create credential", error);
        } finally {
            setSavingId(null);
        }
    };

    const handleSetDefault = async (id: string) => {
        setSavingId(id);
        try {
            await fetch(`${API_ENDPOINTS.CREDENTIALS}/${id}/set-default`, { method: "POST" });
            await fetchCredentials();
            onCredentialChange?.();
        } catch (error) {
            console.error("Failed to set default", error);
        } finally {
            setSavingId(null);
        }
    };

    const handleDelete = async (id: string) => {
        setDeletingId(id);
        try {
            await fetch(`${API_ENDPOINTS.CREDENTIALS}/${id}`, { method: "DELETE" });
            await fetchCredentials();
            onCredentialChange?.();
        } catch (error) {
            console.error("Failed to delete credential", error);
        } finally {
            setDeletingId(null);
        }
    };

    const handleTest = async (id: string) => {
        setTestingId(id);
        setTestResult(null);
        try {
            const res = await fetch(`${API_ENDPOINTS.CREDENTIALS}/${id}/test`, { method: "POST" });
            const data = await res.json();
            setTestResult({ id, success: data.success, message: data.message });
        } catch (error) {
            setTestResult({ id, success: false, message: "Connection failed" });
        } finally {
            setTestingId(null);
        }
    };

    const getProviderInfo = (providerId: string) => {
        return CREDENTIAL_PROVIDERS.find(p => p.id === providerId) || CREDENTIAL_PROVIDERS[6]; // Default to 'other'
    };

    const getCredentialsByProvider = (providerId: string) => {
        return credentials.filter(c => c.provider === providerId);
    };

    const formatLastUsed = (dateStr?: string) => {
        if (!dateStr) return "Never";
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 1) return "Just now";
        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
            </div>
        );
    }

    return (
        <Card className="bg-slate-900 border-slate-800 shadow-xl">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Key className="w-5 h-5 text-amber-400" />
                            API Credentials
                        </CardTitle>
                        <CardDescription className="text-slate-400">
                            Manage API keys for LLM providers. Keys are encrypted at rest.
                        </CardDescription>
                    </div>
                    <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
                        <DialogTrigger asChild>
                            <Button className="bg-indigo-600 hover:bg-indigo-700">
                                <Plus className="w-4 h-4 mr-2" />
                                Add Credential
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="bg-slate-950 border-slate-800 text-white">
                            <DialogHeader>
                                <DialogTitle>Add API Credential</DialogTitle>
                                <DialogDescription className="text-slate-400">
                                    Add a new API key for an LLM provider.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4 py-4">
                                {/* Provider Selection */}
                                <div className="space-y-2">
                                    <Label>Provider</Label>
                                    <div className="grid grid-cols-4 gap-2">
                                        {CREDENTIAL_PROVIDERS.map((p) => (
                                            <button
                                                key={p.id}
                                                onClick={() => {
                                                    setNewCredential({
                                                        ...newCredential,
                                                        provider: p.id,
                                                        base_url: p.defaultUrl,
                                                    });
                                                }}
                                                className={cn(
                                                    "p-3 rounded-lg border text-center transition-all",
                                                    newCredential.provider === p.id
                                                        ? "border-indigo-500 bg-indigo-500/20"
                                                        : "border-slate-700 hover:border-slate-600"
                                                )}
                                            >
                                                <span className="text-2xl">{p.icon}</span>
                                                <p className="text-xs mt-1 text-slate-300">{p.name}</p>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Name */}
                                <div className="space-y-2">
                                    <Label htmlFor="cred-name">Name</Label>
                                    <Input
                                        id="cred-name"
                                        placeholder="e.g., Production Key"
                                        value={newCredential.name}
                                        onChange={(e) => setNewCredential({ ...newCredential, name: e.target.value })}
                                        className="bg-slate-900 border-slate-700"
                                    />
                                </div>

                                {/* API Key */}
                                <div className="space-y-2">
                                    <Label htmlFor="cred-key">API Key</Label>
                                    <Input
                                        id="cred-key"
                                        type="password"
                                        placeholder="sk-..."
                                        value={newCredential.api_key}
                                        onChange={(e) => setNewCredential({ ...newCredential, api_key: e.target.value })}
                                        className="bg-slate-900 border-slate-700 font-mono"
                                    />
                                </div>

                                {/* Base URL (optional) */}
                                <div className="space-y-2">
                                    <Label htmlFor="cred-url">Base URL (optional)</Label>
                                    <Input
                                        id="cred-url"
                                        placeholder="https://api.example.com/v1"
                                        value={newCredential.base_url}
                                        onChange={(e) => setNewCredential({ ...newCredential, base_url: e.target.value })}
                                        className="bg-slate-900 border-slate-700 font-mono text-sm"
                                    />
                                </div>

                                {/* Set as default */}
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={newCredential.is_default}
                                        onChange={(e) => setNewCredential({ ...newCredential, is_default: e.target.checked })}
                                        className="rounded border-slate-600"
                                    />
                                    <span className="text-sm text-slate-300">Set as default for this provider</span>
                                </label>
                            </div>
                            <DialogFooter>
                                <Button variant="ghost" onClick={() => setShowAddModal(false)}>
                                    Cancel
                                </Button>
                                <Button
                                    onClick={handleCreate}
                                    disabled={!newCredential.provider || !newCredential.name || !newCredential.api_key || savingId === "new"}
                                    className="bg-indigo-600 hover:bg-indigo-700"
                                >
                                    {savingId === "new" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                                    Create Credential
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>
            </CardHeader>

            <CardContent className="space-y-6">
                {/* Provider Cards Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {CREDENTIAL_PROVIDERS.slice(0, -1).map((provider) => {
                        const providerCreds = getCredentialsByProvider(provider.id);
                        const hasDefault = providerCreds.some(c => c.is_default);

                        return (
                            <button
                                key={provider.id}
                                onClick={() => setSelectedProvider(
                                    selectedProvider === provider.id ? null : provider.id
                                )}
                                className={cn(
                                    "relative p-4 rounded-xl border transition-all text-left",
                                    selectedProvider === provider.id
                                        ? "border-indigo-500 bg-indigo-500/10"
                                        : "border-slate-800 hover:border-slate-700 hover:bg-slate-800/50"
                                )}
                            >
                                <div className="flex items-start justify-between">
                                    <span className="text-3xl">{provider.icon}</span>
                                    {hasDefault && (
                                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                    )}
                                </div>
                                <h3 className="font-medium text-white mt-2">{provider.name}</h3>
                                <p className="text-xs text-slate-500 mt-1">
                                    {providerCreds.length} credential{providerCreds.length !== 1 ? 's' : ''}
                                </p>
                            </button>
                        );
                    })}
                </div>

                {/* Credentials List for Selected Provider */}
                {selectedProvider && (
                    <div className="space-y-3 pt-4 border-t border-slate-800">
                        <div className="flex items-center gap-2 mb-4">
                            <span className="text-2xl">{getProviderInfo(selectedProvider).icon}</span>
                            <h3 className="text-lg font-medium text-white">
                                {getProviderInfo(selectedProvider).name} Credentials
                            </h3>
                        </div>

                        {getCredentialsByProvider(selectedProvider).length === 0 ? (
                            <div className="text-center py-8 text-slate-500 bg-slate-800/30 rounded-lg border border-dashed border-slate-700">
                                <Key className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                <p>No credentials configured.</p>
                                <Button
                                    variant="link"
                                    className="text-indigo-400 mt-2"
                                    onClick={() => {
                                        setNewCredential({
                                            ...newCredential,
                                            provider: selectedProvider,
                                            base_url: getProviderInfo(selectedProvider).defaultUrl
                                        });
                                        setShowAddModal(true);
                                    }}
                                >
                                    Add your first credential
                                </Button>
                            </div>
                        ) : (
                            getCredentialsByProvider(selectedProvider).map((cred) => (
                                <div
                                    key={cred.id}
                                    className={cn(
                                        "p-4 rounded-lg border transition-all",
                                        cred.is_default
                                            ? "border-emerald-500/30 bg-emerald-500/5"
                                            : "border-slate-800 bg-slate-800/30"
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                {cred.is_default && (
                                                    <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                                                )}
                                                <span className="font-medium text-white">{cred.name}</span>
                                                {cred.is_default && (
                                                    <Badge className="bg-emerald-500/20 text-emerald-400 text-[10px]">
                                                        DEFAULT
                                                    </Badge>
                                                )}
                                            </div>
                                            <div className="mt-1 flex items-center gap-3 text-sm">
                                                <code className="text-slate-500 font-mono">
                                                    {cred.api_key_masked}
                                                </code>
                                                {cred.last_used_at && (
                                                    <span className="text-slate-600 flex items-center gap-1">
                                                        <Clock className="w-3 h-3" />
                                                        {formatLastUsed(cred.last_used_at)}
                                                    </span>
                                                )}
                                            </div>

                                            {/* Test Result */}
                                            {testResult?.id === cred.id && (
                                                <div className={cn(
                                                    "mt-2 text-xs flex items-center gap-1",
                                                    testResult.success ? "text-emerald-400" : "text-red-400"
                                                )}>
                                                    {testResult.success ? (
                                                        <CheckCircle2 className="w-3 h-3" />
                                                    ) : (
                                                        <XCircle className="w-3 h-3" />
                                                    )}
                                                    {testResult.message}
                                                </div>
                                            )}
                                        </div>

                                        <div className="flex items-center gap-1">
                                            {/* Test Button */}
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => handleTest(cred.id)}
                                                disabled={testingId === cred.id}
                                                className="text-slate-400 hover:text-white"
                                            >
                                                {testingId === cred.id ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <TestTube className="w-4 h-4" />
                                                )}
                                            </Button>

                                            {/* Set Default Button */}
                                            {!cred.is_default && (
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => handleSetDefault(cred.id)}
                                                    disabled={savingId === cred.id}
                                                    className="text-slate-400 hover:text-amber-400"
                                                    title="Set as default"
                                                >
                                                    {savingId === cred.id ? (
                                                        <Loader2 className="w-4 h-4 animate-spin" />
                                                    ) : (
                                                        <StarOff className="w-4 h-4" />
                                                    )}
                                                </Button>
                                            )}

                                            {/* Delete Button */}
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => handleDelete(cred.id)}
                                                disabled={deletingId === cred.id}
                                                className="text-slate-400 hover:text-red-400"
                                            >
                                                {deletingId === cred.id ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <Trash2 className="w-4 h-4" />
                                                )}
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {/* Empty state when no provider selected */}
                {!selectedProvider && credentials.length === 0 && (
                    <div className="text-center py-8 text-slate-500 bg-slate-800/30 rounded-lg border border-dashed border-slate-700">
                        <Key className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p>No API credentials configured yet.</p>
                        <p className="text-sm mt-1">Click "Add Credential" to get started.</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
