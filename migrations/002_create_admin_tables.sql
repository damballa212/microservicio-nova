-- Migration: Create admin tables for dynamic configuration
-- Date: 2025-12-26
-- Description: Creates tables for system configuration, prompts, and users in 'chatbot' schema

-- ============================================================================
-- PASO 1: Tabla de Configuraciones del Sistema (Key-Value)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chatbot.system_configs (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by TEXT -- Email or ID of user who updated it
);

COMMENT ON TABLE chatbot.system_configs IS 
    'Dynamic system configurations (e.g., current_model, temperature)';

-- ============================================================================
-- PASO 2: Tabla de Plantillas de Prompts
-- ============================================================================
CREATE TABLE IF NOT EXISTS chatbot.prompt_templates (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE, -- e.g., 'core_system', 'vertical_restaurant'
    content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by TEXT
);

COMMENT ON TABLE chatbot.prompt_templates IS 
    'Versioned prompt templates for core, verticals, and tenants';

-- ============================================================================
-- PASO 3: Tabla de Usuarios Admin (Simple Auth)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chatbot.users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'admin', -- 'admin', 'viewer'
    full_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE chatbot.users IS 
    'Admin users for the Nova Dashboard';

-- ============================================================================
-- PASO 4: Triggers de actualización
-- ============================================================================

-- Trigger para system_configs
CREATE TRIGGER trigger_update_chatbot_system_configs_timestamp
    BEFORE UPDATE ON chatbot.system_configs
    FOR EACH ROW
    EXECUTE FUNCTION chatbot.update_conversation_history_timestamp();

-- Trigger para prompt_templates
CREATE TRIGGER trigger_update_chatbot_prompt_templates_timestamp
    BEFORE UPDATE ON chatbot.prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION chatbot.update_conversation_history_timestamp();

-- Trigger para users
CREATE TRIGGER trigger_update_chatbot_users_timestamp
    BEFORE UPDATE ON chatbot.users
    FOR EACH ROW
    EXECUTE FUNCTION chatbot.update_conversation_history_timestamp();

-- ============================================================================
-- PASO 5: Seed Data (Datos Iniciales)
-- ============================================================================

-- Configuración por defecto
INSERT INTO chatbot.system_configs (key, value, description) VALUES
    ('llm_model', 'openai/gpt-4o-mini', 'Modelo de IA activo'),
    ('llm_temperature', '0.7', 'Temperatura de generación (0.0 - 2.0)'),
    ('llm_max_tokens', '1000', 'Límite de tokens de salida')
ON CONFLICT (key) DO NOTHING;

-- Usuario Admin por defecto (Password: admin123 - DEBE CAMBIARSE EN PROD)
-- Hash es para "admin123" usando bcrypt (ejemplo, se debe generar uno real en backend)
-- Por seguridad, insertamos un placeholder, el usuario deberá crearse via script/API
-- INSERT INTO chatbot.users (email, password_hash, full_name) ...
