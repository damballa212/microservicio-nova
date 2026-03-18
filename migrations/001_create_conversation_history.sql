-- Migration: Create conversation_history table for permanent memory
-- Date: 2024-12-22
-- Description: Implementa persistencia permanente de historial conversacional
--             con schema dedicado para aislar del CRM Flowify

-- ============================================================================
-- PASO 1: Crear schema dedicado para el chatbot
-- ============================================================================
-- Esto asegura separación total de las tablas de Flowify (schema 'public')
-- y de las tablas de RAG (schema 'rag')
CREATE SCHEMA IF NOT EXISTS chatbot;

-- Establecer permisos en el schema
-- GRANT USAGE ON SCHEMA chatbot TO chatbot_user;
-- GRANT CREATE ON SCHEMA chatbot TO chatbot_user;

-- ============================================================================
-- PASO 2: Extensiones requeridas
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PASO 3: Crear tabla de historial conversacional
-- ============================================================================
CREATE TABLE IF NOT EXISTS chatbot.conversation_history (
    id BIGSERIAL PRIMARY KEY,
    identifier TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- PASO 4: Crear índices para eficiencia
-- ============================================================================
-- Índice por identifier (usuario/conversación)
CREATE INDEX IF NOT EXISTS idx_chatbot_conversation_history_identifier 
    ON chatbot.conversation_history(identifier);

-- Índice por fecha de creación (para búsquedas temporales)
CREATE INDEX IF NOT EXISTS idx_chatbot_conversation_history_created_at 
    ON chatbot.conversation_history(created_at DESC);

-- Índice compuesto (identifier + created_at) para queries comunes
CREATE INDEX IF NOT EXISTS idx_chatbot_conversation_history_identifier_created 
    ON chatbot.conversation_history(identifier, created_at DESC);

-- Índice GIN para búsquedas en metadata JSONB
CREATE INDEX IF NOT EXISTS idx_chatbot_conversation_history_metadata 
    ON chatbot.conversation_history USING GIN (metadata);

-- ============================================================================
-- PASO 5: Funciones y Triggers
-- ============================================================================
-- Función para actualizar timestamp automáticamente
CREATE OR REPLACE FUNCTION chatbot.update_conversation_history_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para auto-actualizar updated_at
DROP TRIGGER IF EXISTS trigger_update_chatbot_conversation_history_timestamp 
    ON chatbot.conversation_history;
    
CREATE TRIGGER trigger_update_chatbot_conversation_history_timestamp
    BEFORE UPDATE ON chatbot.conversation_history
    FOR EACH ROW
    EXECUTE FUNCTION chatbot.update_conversation_history_timestamp();

-- ============================================================================
-- PASO 6: Documentación (Comentarios)
-- ============================================================================
COMMENT ON SCHEMA chatbot IS 
    'Schema dedicado para el microservicio de chatbot WhatsApp. Separado de Flowify CRM (public) y RAG (rag).';

COMMENT ON TABLE chatbot.conversation_history IS 
    'Persistent storage for chatbot conversation history';
    
COMMENT ON COLUMN chatbot.conversation_history.identifier IS 
    'Unique identifier for the user/conversation (e.g., phone number, user ID)';
    
COMMENT ON COLUMN chatbot.conversation_history.role IS 
    'Role of the message sender: user, assistant, or system';
    
COMMENT ON COLUMN chatbot.conversation_history.content IS 
    'The actual message content';
    
COMMENT ON COLUMN chatbot.conversation_history.metadata IS 
    'Additional metadata: tokens used, model name, processing time, etc.';
    
COMMENT ON COLUMN chatbot.conversation_history.created_at IS 
    'Timestamp when the message was created';

-- ============================================================================
-- PASO 7: Permisos (opcional - descomentar y ajustar según necesidad)
-- ============================================================================
-- GRANT SELECT, INSERT ON chatbot.conversation_history TO chatbot_user;
-- GRANT USAGE, SELECT ON SEQUENCE chatbot.conversation_history_id_seq TO chatbot_user;
