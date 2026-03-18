/**
 * Enterprise Model Selector Constants
 * OpenRouter-centric model configuration for Nova AI
 */

export const SETTINGS_LABELS: Record<string, string> = {
    "llm_model": "AI Model Provider",
    "llm_temperature": "Creativity Level (Temperature)",
    "llm_max_tokens": "Max Response Length (Tokens)",
    "openai_api_key": "OpenAI API Key",
    "google_api_key": "Google Gemini API Key"
};

// Provider definitions with icons and metadata
export interface Provider {
    id: string;
    name: string;
    description: string;
    icon: string; // Lucide icon name or emoji
    color: string; // Tailwind color class
    modelCount?: number;
}

export const PROVIDERS: Provider[] = [
    { id: "openrouter", name: "OpenRouter", description: "Unified API for 300+ models", icon: "🔀", color: "from-pink-500 to-rose-500" },
    { id: "openai", name: "OpenAI", description: "GPT-4, GPT-5, o1, o3 series", icon: "🤖", color: "from-emerald-500 to-teal-500" },
    { id: "anthropic", name: "Anthropic", description: "Claude 3.5, 3.7, 4.5 series", icon: "🧠", color: "from-orange-500 to-amber-500" },
    { id: "google", name: "Google", description: "Gemini 2.5, 3.0 series", icon: "✨", color: "from-blue-500 to-indigo-500" },
    { id: "meta", name: "Meta", description: "Llama 3, 4 series", icon: "🦙", color: "from-blue-600 to-blue-400" },
    { id: "mistral", name: "Mistral AI", description: "Mistral, Mixtral, Codestral", icon: "🌀", color: "from-violet-500 to-purple-500" },
    { id: "deepseek", name: "DeepSeek", description: "DeepSeek R1, V3 series", icon: "🔍", color: "from-cyan-500 to-sky-500" },
    { id: "qwen", name: "Qwen", description: "Qwen 2.5, 3 series", icon: "🐉", color: "from-red-500 to-orange-500" },
    { id: "other", name: "Other Providers", description: "xAI, Cohere, Nvidia, etc.", icon: "🌐", color: "from-slate-500 to-gray-500" },
];

// Complete OpenRouter model list (user-provided)
export const ALL_MODELS: string[] = [
    // AI21
    "ai21/jamba-large-1.7",
    "ai21/jamba-mini-1.7",
    // Aion Labs
    "aion-labs/aion-1.0",
    "aion-labs/aion-1.0-mini",
    "aion-labs/aion-rp-llama-3.1-8b",
    // Alfredpros
    "alfredpros/codellama-7b-instruct-solidity",
    // Alibaba
    "alibaba/tongyi-deepresearch-30b-a3b",
    "alibaba/tongyi-deepresearch-30b-a3b:free",
    // AllenAI
    "allenai/olmo-2-0325-32b-instruct",
    "allenai/olmo-3-32b-think:free",
    "allenai/olmo-3-7b-instruct",
    "allenai/olmo-3-7b-think",
    "allenai/olmo-3.1-32b-think:free",
    // Alpindale
    "alpindale/goliath-120b",
    // Amazon
    "amazon/nova-2-lite-v1",
    "amazon/nova-lite-v1",
    "amazon/nova-micro-v1",
    "amazon/nova-premier-v1",
    "amazon/nova-pro-v1",
    // Anthracite
    "anthracite-org/magnum-v4-72b",
    // Anthropic
    "anthropic/claude-3-haiku",
    "anthropic/claude-3-opus",
    "anthropic/claude-3.5-haiku",
    "anthropic/claude-3.5-haiku-20241022",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.7-sonnet",
    "anthropic/claude-3.7-sonnet:thinking",
    "anthropic/claude-haiku-4.5",
    "anthropic/claude-opus-4",
    "anthropic/claude-opus-4.1",
    "anthropic/claude-opus-4.5",
    "anthropic/claude-sonnet-4",
    "anthropic/claude-sonnet-4.5",
    // Arcee
    "arcee-ai/coder-large",
    "arcee-ai/maestro-reasoning",
    "arcee-ai/spotlight",
    "arcee-ai/trinity-mini",
    "arcee-ai/trinity-mini:free",
    "arcee-ai/virtuoso-large",
    // ArliAI
    "arliai/qwq-32b-arliai-rpr-v1",
    // Baidu
    "baidu/ernie-4.5-21b-a3b",
    "baidu/ernie-4.5-21b-a3b-thinking",
    "baidu/ernie-4.5-300b-a47b",
    "baidu/ernie-4.5-vl-28b-a3b",
    "baidu/ernie-4.5-vl-424b-a47b",
    // ByteDance
    "bytedance-seed/seed-1.6",
    "bytedance-seed/seed-1.6-flash",
    "bytedance/ui-tars-1.5-7b",
    // Cognitive Computations
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    // Cohere
    "cohere/command-a",
    "cohere/command-r-08-2024",
    "cohere/command-r-plus-08-2024",
    "cohere/command-r7b-12-2024",
    // DeepCogito
    "deepcogito/cogito-v2-preview-llama-109b-moe",
    "deepcogito/cogito-v2-preview-llama-405b",
    "deepcogito/cogito-v2-preview-llama-70b",
    "deepcogito/cogito-v2.1-671b",
    // DeepSeek
    "deepseek/deepseek-chat",
    "deepseek/deepseek-chat-v3-0324",
    "deepseek/deepseek-chat-v3.1",
    "deepseek/deepseek-prover-v2",
    "deepseek/deepseek-r1",
    "deepseek/deepseek-r1-0528",
    "deepseek/deepseek-r1-0528-qwen3-8b",
    "deepseek/deepseek-r1-0528:free",
    "deepseek/deepseek-r1-distill-llama-70b",
    "deepseek/deepseek-r1-distill-qwen-14b",
    "deepseek/deepseek-r1-distill-qwen-32b",
    "deepseek/deepseek-v3.1-terminus",
    "deepseek/deepseek-v3.1-terminus:exacto",
    "deepseek/deepseek-v3.2",
    "deepseek/deepseek-v3.2-exp",
    "deepseek/deepseek-v3.2-speciale",
    // EleutherAI
    "eleutherai/llemma_7b",
    // EssentialAI
    "essentialai/rnj-1-instruct",
    // Google
    "google/gemini-2.0-flash-001",
    "google/gemini-2.0-flash-exp:free",
    "google/gemini-2.0-flash-lite-001",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-flash-image",
    "google/gemini-2.5-flash-image-preview",
    "google/gemini-2.5-flash-lite",
    "google/gemini-2.5-flash-lite-preview-09-2025",
    "google/gemini-2.5-flash-preview-09-2025",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-pro-preview",
    "google/gemini-2.5-pro-preview-05-06",
    "google/gemini-3-flash-preview",
    "google/gemini-3-pro-image-preview",
    "google/gemini-3-pro-preview",
    "google/gemma-2-27b-it",
    "google/gemma-2-9b-it",
    "google/gemma-3-12b-it",
    "google/gemma-3-12b-it:free",
    "google/gemma-3-27b-it",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-4b-it",
    "google/gemma-3-4b-it:free",
    "google/gemma-3n-e2b-it:free",
    "google/gemma-3n-e4b-it",
    "google/gemma-3n-e4b-it:free",
    // Gryphe
    "gryphe/mythomax-l2-13b",
    // IBM Granite
    "ibm-granite/granite-4.0-h-micro",
    // Inception
    "inception/mercury",
    "inception/mercury-coder",
    // Inflection
    "inflection/inflection-3-pi",
    "inflection/inflection-3-productivity",
    // KwaiPilot
    "kwaipilot/kat-coder-pro:free",
    // Liquid
    "liquid/lfm-2.2-6b",
    "liquid/lfm2-8b-a1b",
    // Mancer
    "mancer/weaver",
    // Meituan
    "meituan/longcat-flash-chat",
    // Meta Llama
    "meta-llama/llama-3-70b-instruct",
    "meta-llama/llama-3-8b-instruct",
    "meta-llama/llama-3.1-405b",
    "meta-llama/llama-3.1-405b-instruct",
    "meta-llama/llama-3.1-405b-instruct:free",
    "meta-llama/llama-3.1-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
    "meta-llama/llama-3.2-11b-vision-instruct",
    "meta-llama/llama-3.2-1b-instruct",
    "meta-llama/llama-3.2-3b-instruct",
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.2-90b-vision-instruct",
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-4-maverick",
    "meta-llama/llama-4-scout",
    "meta-llama/llama-guard-2-8b",
    "meta-llama/llama-guard-3-8b",
    "meta-llama/llama-guard-4-12b",
    // Microsoft
    "microsoft/phi-3-medium-128k-instruct",
    "microsoft/phi-3-mini-128k-instruct",
    "microsoft/phi-3.5-mini-128k-instruct",
    "microsoft/phi-4",
    "microsoft/phi-4-multimodal-instruct",
    "microsoft/phi-4-reasoning-plus",
    "microsoft/wizardlm-2-8x22b",
    // MiniMax
    "minimax/minimax-01",
    "minimax/minimax-m1",
    "minimax/minimax-m2",
    "minimax/minimax-m2.1",
    // Mistral AI
    "mistralai/codestral-2508",
    "mistralai/devstral-2512",
    "mistralai/devstral-2512:free",
    "mistralai/devstral-medium",
    "mistralai/devstral-small",
    "mistralai/devstral-small-2505",
    "mistralai/ministral-14b-2512",
    "mistralai/ministral-3b",
    "mistralai/ministral-3b-2512",
    "mistralai/ministral-8b",
    "mistralai/ministral-8b-2512",
    "mistralai/mistral-7b-instruct",
    "mistralai/mistral-7b-instruct-v0.1",
    "mistralai/mistral-7b-instruct-v0.2",
    "mistralai/mistral-7b-instruct-v0.3",
    "mistralai/mistral-7b-instruct:free",
    "mistralai/mistral-large",
    "mistralai/mistral-large-2407",
    "mistralai/mistral-large-2411",
    "mistralai/mistral-large-2512",
    "mistralai/mistral-medium-3",
    "mistralai/mistral-medium-3.1",
    "mistralai/mistral-nemo",
    "mistralai/mistral-saba",
    "mistralai/mistral-small-24b-instruct-2501",
    "mistralai/mistral-small-3.1-24b-instruct",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "mistralai/mistral-small-3.2-24b-instruct",
    "mistralai/mistral-small-creative",
    "mistralai/mistral-tiny",
    "mistralai/mixtral-8x22b-instruct",
    "mistralai/mixtral-8x7b-instruct",
    "mistralai/pixtral-12b",
    "mistralai/pixtral-large-2411",
    "mistralai/voxtral-small-24b-2507",
    // Moonshot AI
    "moonshotai/kimi-dev-72b",
    "moonshotai/kimi-k2",
    "moonshotai/kimi-k2-0905",
    "moonshotai/kimi-k2-0905:exacto",
    "moonshotai/kimi-k2-thinking",
    "moonshotai/kimi-k2:free",
    // Morph
    "morph/morph-v3-fast",
    "morph/morph-v3-large",
    // NeverSleep
    "neversleep/llama-3.1-lumimaid-8b",
    "neversleep/noromaid-20b",
    // Nex AGI
    "nex-agi/deepseek-v3.1-nex-n1:free",
    // NousResearch
    "nousresearch/deephermes-3-mistral-24b-preview",
    "nousresearch/hermes-2-pro-llama-3-8b",
    "nousresearch/hermes-3-llama-3.1-405b",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "nousresearch/hermes-3-llama-3.1-70b",
    "nousresearch/hermes-4-405b",
    "nousresearch/hermes-4-70b",
    // Nvidia
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-12b-v2-vl",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-nano-9b-v2",
    "nvidia/nemotron-nano-9b-v2:free",
    // OpenAI
    "openai/chatgpt-4o-latest",
    "openai/codex-mini",
    "openai/gpt-3.5-turbo",
    "openai/gpt-3.5-turbo-0613",
    "openai/gpt-3.5-turbo-16k",
    "openai/gpt-3.5-turbo-instruct",
    "openai/gpt-4",
    "openai/gpt-4-0314",
    "openai/gpt-4-1106-preview",
    "openai/gpt-4-turbo",
    "openai/gpt-4-turbo-preview",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4.1-nano",
    "openai/gpt-4o",
    "openai/gpt-4o-2024-05-13",
    "openai/gpt-4o-2024-08-06",
    "openai/gpt-4o-2024-11-20",
    "openai/gpt-4o-audio-preview",
    "openai/gpt-4o-mini",
    "openai/gpt-4o-mini-2024-07-18",
    "openai/gpt-4o-mini-search-preview",
    "openai/gpt-4o-search-preview",
    "openai/gpt-4o:extended",
    "openai/gpt-5",
    "openai/gpt-5-chat",
    "openai/gpt-5-codex",
    "openai/gpt-5-image",
    "openai/gpt-5-image-mini",
    "openai/gpt-5-mini",
    "openai/gpt-5-nano",
    "openai/gpt-5-pro",
    "openai/gpt-5.1",
    "openai/gpt-5.1-chat",
    "openai/gpt-5.1-codex",
    "openai/gpt-5.1-codex-max",
    "openai/gpt-5.1-codex-mini",
    "openai/gpt-5.2",
    "openai/gpt-5.2-chat",
    "openai/gpt-5.2-pro",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-120b:exacto",
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-safeguard-20b",
    "openai/o1",
    "openai/o1-pro",
    "openai/o3",
    "openai/o3-deep-research",
    "openai/o3-mini",
    "openai/o3-mini-high",
    "openai/o3-pro",
    "openai/o4-mini",
    "openai/o4-mini-deep-research",
    "openai/o4-mini-high",
    // OpenGVLab
    "opengvlab/internvl3-78b",
    // OpenRouter
    "openrouter/auto",
    "openrouter/bodybuilder",
    // Perplexity
    "perplexity/sonar",
    "perplexity/sonar-deep-research",
    "perplexity/sonar-pro",
    "perplexity/sonar-pro-search",
    "perplexity/sonar-reasoning",
    "perplexity/sonar-reasoning-pro",
    // Prime Intellect
    "prime-intellect/intellect-3",
    // Qwen
    "qwen/qwen-2.5-72b-instruct",
    "qwen/qwen-2.5-7b-instruct",
    "qwen/qwen-2.5-coder-32b-instruct",
    "qwen/qwen-2.5-vl-7b-instruct",
    "qwen/qwen-2.5-vl-7b-instruct:free",
    "qwen/qwen-max",
    "qwen/qwen-plus",
    "qwen/qwen-plus-2025-07-28",
    "qwen/qwen-plus-2025-07-28:thinking",
    "qwen/qwen-turbo",
    "qwen/qwen-vl-max",
    "qwen/qwen-vl-plus",
    "qwen/qwen2.5-coder-7b-instruct",
    "qwen/qwen2.5-vl-32b-instruct",
    "qwen/qwen2.5-vl-72b-instruct",
    "qwen/qwen3-14b",
    "qwen/qwen3-235b-a22b",
    "qwen/qwen3-235b-a22b-2507",
    "qwen/qwen3-235b-a22b-thinking-2507",
    "qwen/qwen3-30b-a3b",
    "qwen/qwen3-30b-a3b-instruct-2507",
    "qwen/qwen3-30b-a3b-thinking-2507",
    "qwen/qwen3-32b",
    "qwen/qwen3-4b:free",
    "qwen/qwen3-8b",
    "qwen/qwen3-coder",
    "qwen/qwen3-coder-30b-a3b-instruct",
    "qwen/qwen3-coder-flash",
    "qwen/qwen3-coder-plus",
    "qwen/qwen3-coder:exacto",
    "qwen/qwen3-coder:free",
    "qwen/qwen3-max",
    "qwen/qwen3-next-80b-a3b-instruct",
    "qwen/qwen3-next-80b-a3b-thinking",
    "qwen/qwen3-vl-235b-a22b-instruct",
    "qwen/qwen3-vl-235b-a22b-thinking",
    "qwen/qwen3-vl-30b-a3b-instruct",
    "qwen/qwen3-vl-30b-a3b-thinking",
    "qwen/qwen3-vl-32b-instruct",
    "qwen/qwen3-vl-8b-instruct",
    "qwen/qwen3-vl-8b-thinking",
    "qwen/qwq-32b",
    // Raifle
    "raifle/sorcererlm-8x22b",
    // Relace
    "relace/relace-apply-3",
    "relace/relace-search",
    // Sao10k
    "sao10k/l3-euryale-70b",
    "sao10k/l3-lunaris-8b",
    "sao10k/l3.1-70b-hanami-x1",
    "sao10k/l3.1-euryale-70b",
    "sao10k/l3.3-euryale-70b",
    // StepFun
    "stepfun-ai/step3",
    // SwitchPoint
    "switchpoint/router",
    // Tencent
    "tencent/hunyuan-a13b-instruct",
    // TheDrummer
    "thedrummer/cydonia-24b-v4.1",
    "thedrummer/rocinante-12b",
    "thedrummer/skyfall-36b-v2",
    "thedrummer/unslopnemo-12b",
    // THUDM
    "thudm/glm-4.1v-9b-thinking",
    // TNG Tech
    "tngtech/deepseek-r1t-chimera",
    "tngtech/deepseek-r1t-chimera:free",
    "tngtech/deepseek-r1t2-chimera",
    "tngtech/deepseek-r1t2-chimera:free",
    "tngtech/tng-r1t-chimera",
    "tngtech/tng-r1t-chimera:free",
    // Undi95
    "undi95/remm-slerp-l2-13b",
    // xAI
    "x-ai/grok-3",
    "x-ai/grok-3-beta",
    "x-ai/grok-3-mini",
    "x-ai/grok-3-mini-beta",
    "x-ai/grok-4",
    "x-ai/grok-4-fast",
    "x-ai/grok-4.1-fast",
    "x-ai/grok-code-fast-1",
    // Xiaomi
    "xiaomi/mimo-v2-flash:free",
    // Z-AI (GLM)
    "z-ai/glm-4-32b",
    "z-ai/glm-4.5",
    "z-ai/glm-4.5-air",
    "z-ai/glm-4.5-air:free",
    "z-ai/glm-4.5v",
    "z-ai/glm-4.6",
    "z-ai/glm-4.6:exacto",
    "z-ai/glm-4.6v",
    "z-ai/glm-4.7",
];

// Helper function to extract provider from model ID
export function getProviderFromModelId(modelId: string): string {
    const prefix = modelId.split('/')[0];
    const providerMap: Record<string, string> = {
        'openai': 'openai',
        'anthropic': 'anthropic',
        'google': 'google',
        'meta-llama': 'meta',
        'mistralai': 'mistral',
        'deepseek': 'deepseek',
        'qwen': 'qwen',
        'x-ai': 'other',
        'nvidia': 'other',
        'cohere': 'other',
        'amazon': 'other',
        'microsoft': 'other',
        'perplexity': 'other',
        'openrouter': 'openrouter',
    };
    return providerMap[prefix] || 'other';
}

// Get models filtered by provider
export function getModelsByProvider(providerId: string): string[] {
    if (providerId === 'openrouter') {
        return ALL_MODELS; // OpenRouter has access to ALL models
    }

    const prefixMap: Record<string, string[]> = {
        'openai': ['openai/'],
        'anthropic': ['anthropic/'],
        'google': ['google/'],
        'meta': ['meta-llama/'],
        'mistral': ['mistralai/'],
        'deepseek': ['deepseek/'],
        'qwen': ['qwen/'],
        'other': [], // Will be computed as "everything else"
    };

    const prefixes = prefixMap[providerId];
    if (!prefixes) return [];

    if (providerId === 'other') {
        const knownPrefixes = Object.values(prefixMap).flat().filter(p => p !== '');
        return ALL_MODELS.filter(m => !knownPrefixes.some(prefix => m.startsWith(prefix)));
    }

    return ALL_MODELS.filter(m => prefixes.some(prefix => m.startsWith(prefix)));
}

// Get friendly name from model ID
export function getModelDisplayName(modelId: string): string {
    const parts = modelId.split('/');
    if (parts.length < 2) return modelId;

    let name = parts[1];
    // Remove common suffixes for cleaner display
    name = name.replace(/:free$/, ' (Free)');
    name = name.replace(/:exacto$/, ' (Exacto)');
    name = name.replace(/:thinking$/, ' (Thinking)');
    // Convert kebab-case to Title Case
    name = name.split('-').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');

    return name;
}
