-- AI Thought Processor Database Schema
-- Enable required extensions

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    context_version INTEGER DEFAULT 1,
    context_updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on email for faster lookups
CREATE INDEX idx_users_email ON users(email);

-- Thoughts table
CREATE TABLE thoughts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Processing status
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    processed_at TIMESTAMPTZ,
    processing_attempts INTEGER DEFAULT 0,
    error_message TEXT,

    -- AI Analysis results (stored as JSONB for flexibility)
    classification JSONB,
    analysis JSONB,
    value_impact JSONB,
    action_plan JSONB,
    priority JSONB,

    -- Metadata
    context_version INTEGER,
    embedding VECTOR(1536),

    -- Performance indexes
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for efficient queries
CREATE INDEX idx_thoughts_user_status ON thoughts(user_id, status);
CREATE INDEX idx_thoughts_created_at ON thoughts(created_at DESC);
CREATE INDEX idx_thoughts_status_pending ON thoughts(status) WHERE status = 'pending';
CREATE INDEX idx_thoughts_embedding ON thoughts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Thought tags table for categorization
CREATE TABLE thought_tags (
    thought_id UUID NOT NULL REFERENCES thoughts(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    confidence FLOAT,
    PRIMARY KEY (thought_id, tag)
);

CREATE INDEX idx_thought_tags_tag ON thought_tags(tag);

-- Weekly synthesis table
CREATE TABLE weekly_synthesis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    synthesis JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, week_start)
);

CREATE INDEX idx_weekly_synthesis_user_week ON weekly_synthesis(user_id, week_start DESC);

-- Semantic cache table for duplicate thought detection
CREATE TABLE thought_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thought_text TEXT NOT NULL,
    embedding VECTOR(1536),
    response JSONB NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

-- Indexes for cache lookups
CREATE INDEX idx_cache_user_embedding ON thought_cache USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_cache_expires ON thought_cache(expires_at) WHERE expires_at > NOW();

-- Function to match similar thoughts using vector similarity
CREATE OR REPLACE FUNCTION match_similar_thoughts(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    user_id_param uuid
)
RETURNS TABLE (
    id uuid,
    thought_text text,
    response jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        thought_cache.id,
        thought_cache.thought_text,
        thought_cache.response,
        1 - (thought_cache.embedding <=> query_embedding) as similarity
    FROM thought_cache
    WHERE
        thought_cache.user_id = user_id_param
        AND thought_cache.expires_at > NOW()
        AND 1 - (thought_cache.embedding <=> query_embedding) > match_threshold
    ORDER BY thought_cache.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM thought_cache WHERE expires_at < NOW();
END;
$$;

-- Function to update user context version
CREATE OR REPLACE FUNCTION update_context_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.context_version := OLD.context_version + 1;
    NEW.context_updated_at := NOW();
    RETURN NEW;
END;
$$;

-- Trigger to auto-increment context version
CREATE TRIGGER trigger_update_context_version
    BEFORE UPDATE ON users
    FOR EACH ROW
    WHEN (OLD.context IS DISTINCT FROM NEW.context)
    EXECUTE FUNCTION update_context_version();

-- Create a view for easy thought retrieval with user context
CREATE VIEW thoughts_with_context AS
SELECT
    t.*,
    u.email,
    u.context as user_context,
    u.context_version as user_context_version
FROM thoughts t
INNER JOIN users u ON t.user_id = u.id;

-- Grant permissions (adjust for your setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO thoughtprocessor;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO thoughtprocessor;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO thoughtprocessor;

-- Comments for documentation
COMMENT ON TABLE users IS 'Stores user profiles and their personal context for thought analysis';
COMMENT ON TABLE thoughts IS 'Main table storing user thoughts and AI-generated analysis';
COMMENT ON TABLE thought_cache IS 'Semantic cache for avoiding duplicate AI processing';
COMMENT ON COLUMN thoughts.embedding IS 'Vector embedding for semantic search (1536 dimensions from OpenAI)';
COMMENT ON FUNCTION match_similar_thoughts IS 'Finds semantically similar cached thoughts using cosine similarity';
