export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Ensure no trailing slash
const baseUrl = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;

export const API_ENDPOINTS = {
    CONFIG: `${baseUrl}/admin/config`,
    CREDENTIALS: `${baseUrl}/admin/credentials`,
    PROMPTS: `${baseUrl}/admin/prompts`,
    RAG: `${baseUrl}/rag`,
};
