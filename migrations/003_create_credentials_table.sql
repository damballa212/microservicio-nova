-- Migration: Create API Credentials Table
-- Nova AI Admin Panel - Credentials Management

-- Create enum for providers
DO $$ BEGIN
    CREATE TYPE chatbot.credential_provider AS ENUM (
        'openrouter',
        'openai',
        'anthropic',
        'google',
        'cohere',
        'mistral',
        'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create credentials table
CREATE TABLE IF NOT EXISTS chatbot.api_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider chatbot.credential_provider NOT NULL,
    name VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    base_url VARCHAR(255),
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure only one default per provider
CREATE UNIQUE INDEX IF NOT EXISTS idx_credentials_default_provider 
ON chatbot.api_credentials (provider) 
WHERE is_default = TRUE;

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_credentials_provider_active 
ON chatbot.api_credentials (provider, is_active);

-- Comment
COMMENT ON TABLE chatbot.api_credentials IS 'Stores encrypted API credentials for LLM providers';
COMMENT ON COLUMN chatbot.api_credentials.api_key_encrypted IS 'Fernet-encrypted API key';
