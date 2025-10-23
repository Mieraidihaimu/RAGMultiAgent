-- Migration 007: Add Persona Groups and Dynamic Agent System
-- This migration adds support for user-defined groups with custom personas
-- Each persona has a simple text prompt that defines their perspective

-- Create persona_groups table (user-owned collections of personas)
CREATE TABLE IF NOT EXISTS persona_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure unique group names per user
    CONSTRAINT unique_user_group_name UNIQUE(user_id, name),
    
    -- Validate name length
    CONSTRAINT group_name_length CHECK (LENGTH(TRIM(name)) >= 1 AND LENGTH(name) <= 100)
);

-- Create personas table (custom agents with simple text prompts)
CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID NOT NULL REFERENCES persona_groups(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Validate name and prompt length
    CONSTRAINT persona_name_length CHECK (LENGTH(TRIM(name)) >= 1 AND LENGTH(name) <= 100),
    CONSTRAINT persona_prompt_length CHECK (LENGTH(TRIM(prompt)) >= 10 AND LENGTH(prompt) <= 2000)
);

-- Create thought_persona_runs table (track which personas processed each thought)
CREATE TABLE IF NOT EXISTS thought_persona_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thought_id UUID NOT NULL REFERENCES thoughts(id) ON DELETE CASCADE,
    persona_id UUID REFERENCES personas(id) ON DELETE SET NULL,
    group_id UUID REFERENCES persona_groups(id) ON DELETE SET NULL,
    persona_name TEXT NOT NULL,  -- Store name in case persona is deleted
    persona_output JSONB,  -- Individual persona's full 5-agent result
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure processing time is reasonable
    CONSTRAINT reasonable_processing_time CHECK (processing_time_ms >= 0 AND processing_time_ms <= 300000)
);

-- Extend thoughts table to support processing modes
ALTER TABLE thoughts 
    ADD COLUMN IF NOT EXISTS processing_mode TEXT DEFAULT 'single' 
        CHECK (processing_mode IN ('single', 'group')),
    ADD COLUMN IF NOT EXISTS group_id UUID REFERENCES persona_groups(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS consolidated_output JSONB;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_persona_groups_user_id ON persona_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_persona_groups_created_at ON persona_groups(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_personas_group_id ON personas(group_id);
CREATE INDEX IF NOT EXISTS idx_personas_sort_order ON personas(group_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_thought_persona_runs_thought_id ON thought_persona_runs(thought_id);
CREATE INDEX IF NOT EXISTS idx_thought_persona_runs_persona_id ON thought_persona_runs(persona_id);
CREATE INDEX IF NOT EXISTS idx_thought_persona_runs_group_id ON thought_persona_runs(group_id);

CREATE INDEX IF NOT EXISTS idx_thoughts_processing_mode ON thoughts(processing_mode);
CREATE INDEX IF NOT EXISTS idx_thoughts_group_id ON thoughts(group_id);

-- Create updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add updated_at triggers
DROP TRIGGER IF EXISTS update_persona_groups_updated_at ON persona_groups;
CREATE TRIGGER update_persona_groups_updated_at
    BEFORE UPDATE ON persona_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_personas_updated_at ON personas;
CREATE TRIGGER update_personas_updated_at
    BEFORE UPDATE ON personas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE persona_groups IS 'User-defined groups containing custom personas for multi-perspective thought analysis';
COMMENT ON TABLE personas IS 'Custom AI personas with simple text prompts defining their perspective/role';
COMMENT ON TABLE thought_persona_runs IS 'Audit log tracking which personas processed each thought';

COMMENT ON COLUMN personas.prompt IS 'Simple text field describing the persona''s context, role, or perspective (e.g., "You are a pragmatic tech lead focused on scalability")';
COMMENT ON COLUMN thoughts.processing_mode IS 'Processing mode: single (personal LLM feedback) or group (multiple persona perspectives)';
COMMENT ON COLUMN thoughts.consolidated_output IS 'AI-synthesized consolidated feedback from all personas (only for group mode)';
COMMENT ON COLUMN thought_persona_runs.persona_output IS 'Full 5-agent analysis result from this specific persona';
