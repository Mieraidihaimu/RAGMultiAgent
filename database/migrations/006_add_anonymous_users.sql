-- Add support for anonymous users with rate limiting
-- This migration creates tables and functions to track anonymous user sessions
-- and enforce a 3-thought limit before requiring signup

-- Anonymous sessions table to track temporary users
CREATE TABLE anonymous_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_token TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    thought_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days',
    converted_to_user_id UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for efficient lookups
CREATE INDEX idx_anonymous_sessions_token ON anonymous_sessions(session_token);
CREATE INDEX idx_anonymous_sessions_ip ON anonymous_sessions(ip_address);
CREATE INDEX idx_anonymous_sessions_expires ON anonymous_sessions(expires_at);

-- Add anonymous_session_id to thoughts table for tracking anonymous thoughts
ALTER TABLE thoughts
ADD COLUMN anonymous_session_id UUID REFERENCES anonymous_sessions(id) ON DELETE SET NULL;

-- Make user_id nullable to support anonymous thoughts
ALTER TABLE thoughts
ALTER COLUMN user_id DROP NOT NULL;

-- Add constraint to ensure either user_id or anonymous_session_id is set
ALTER TABLE thoughts
ADD CONSTRAINT thoughts_user_or_anonymous_check 
CHECK (
    (user_id IS NOT NULL AND anonymous_session_id IS NULL) OR
    (user_id IS NULL AND anonymous_session_id IS NOT NULL)
);

-- Add index for anonymous thoughts lookup
CREATE INDEX idx_thoughts_anonymous_session ON thoughts(anonymous_session_id) WHERE anonymous_session_id IS NOT NULL;

-- Function to cleanup expired anonymous sessions
CREATE OR REPLACE FUNCTION cleanup_expired_anonymous_sessions()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- Delete sessions that have expired and haven't been converted
    DELETE FROM anonymous_sessions 
    WHERE expires_at < NOW() 
    AND converted_to_user_id IS NULL;
END;
$$;

-- Function to increment thought count for anonymous session
CREATE OR REPLACE FUNCTION increment_anonymous_thought_count(
    p_session_token TEXT
)
RETURNS TABLE (
    thought_count INTEGER,
    limit_reached BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_thought_count INTEGER;
    v_limit INTEGER := 3;
BEGIN
    -- Update the thought count and last activity
    UPDATE anonymous_sessions as a
    SET 
        thought_count = a.thought_count + 1,
        last_activity_at = NOW()
    WHERE a.session_token = p_session_token
    RETURNING a.thought_count INTO v_thought_count;

    -- Return the updated count and whether limit is reached
    RETURN QUERY SELECT v_thought_count, v_thought_count >= v_limit;
END;
$$;

-- Function to convert anonymous thoughts to registered user
CREATE OR REPLACE FUNCTION convert_anonymous_to_user(
    p_session_token TEXT,
    p_user_id UUID
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_session_id UUID;
    v_thoughts_converted INTEGER;
BEGIN
    -- Get the session ID
    SELECT id INTO v_session_id
    FROM anonymous_sessions
    WHERE session_token = p_session_token
    AND expires_at > NOW();

    IF v_session_id IS NULL THEN
        RETURN 0;
    END IF;

    -- Transfer all thoughts to the user
    UPDATE thoughts
    SET 
        user_id = p_user_id,
        anonymous_session_id = NULL
    WHERE anonymous_session_id = v_session_id;

    GET DIAGNOSTICS v_thoughts_converted = ROW_COUNT;

    -- Mark the session as converted
    UPDATE anonymous_sessions
    SET converted_to_user_id = p_user_id
    WHERE id = v_session_id;

    RETURN v_thoughts_converted;
END;
$$;

-- Comments for documentation
COMMENT ON TABLE anonymous_sessions IS 'Tracks anonymous user sessions with rate limiting (max 3 thoughts before signup)';
COMMENT ON COLUMN thoughts.anonymous_session_id IS 'Links thought to anonymous session for pre-signup users';
COMMENT ON FUNCTION cleanup_expired_anonymous_sessions IS 'Removes expired anonymous sessions that were not converted to registered users';
COMMENT ON FUNCTION increment_anonymous_thought_count IS 'Increments thought count for anonymous session and returns limit status';
COMMENT ON FUNCTION convert_anonymous_to_user IS 'Transfers all anonymous thoughts to a registered user account upon signup';
