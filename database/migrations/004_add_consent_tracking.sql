-- Migration: Add consent tracking for GDPR/CCPA compliance
-- Purpose: Track user consent for various data processing activities
-- Date: 2025-10-22

-- Add consent tracking columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS consent_terms_accepted BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS consent_terms_accepted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS consent_terms_version VARCHAR(20),
ADD COLUMN IF NOT EXISTS consent_privacy_accepted BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS consent_privacy_accepted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS consent_privacy_version VARCHAR(20),
ADD COLUMN IF NOT EXISTS consent_marketing BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS consent_marketing_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS consent_analytics BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS consent_analytics_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS consent_data_processing BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS consent_data_processing_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS consent_ip_address VARCHAR(45),
ADD COLUMN IF NOT EXISTS consent_user_agent TEXT,
ADD COLUMN IF NOT EXISTS data_retention_acknowledged BOOLEAN DEFAULT FALSE NOT NULL;

-- Create consent history audit log table
CREATE TABLE IF NOT EXISTS consent_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(50) NOT NULL, -- 'terms', 'privacy', 'marketing', 'analytics', 'data_processing'
    consent_given BOOLEAN NOT NULL,
    consent_version VARCHAR(20),
    consent_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    action VARCHAR(20) NOT NULL, -- 'signup', 'update', 'withdraw', 'renew'
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_consent_history_user_id ON consent_history(user_id);
CREATE INDEX IF NOT EXISTS idx_consent_history_type ON consent_history(consent_type);
CREATE INDEX IF NOT EXISTS idx_consent_history_timestamp ON consent_history(consent_timestamp);
CREATE INDEX IF NOT EXISTS idx_users_consent_terms ON users(consent_terms_accepted);
CREATE INDEX IF NOT EXISTS idx_users_consent_privacy ON users(consent_privacy_accepted);

-- Create a view for current user consent status
CREATE OR REPLACE VIEW user_consent_status AS
SELECT
    u.id,
    u.email,
    u.consent_terms_accepted,
    u.consent_terms_accepted_at,
    u.consent_terms_version,
    u.consent_privacy_accepted,
    u.consent_privacy_accepted_at,
    u.consent_privacy_version,
    u.consent_marketing,
    u.consent_marketing_at,
    u.consent_analytics,
    u.consent_analytics_at,
    u.consent_data_processing,
    u.consent_data_processing_at,
    u.data_retention_acknowledged,
    CASE
        WHEN u.consent_terms_accepted AND u.consent_privacy_accepted THEN 'compliant'
        ELSE 'incomplete'
    END AS compliance_status,
    u.created_at AS user_created_at
FROM users u;

-- Function to log consent changes
CREATE OR REPLACE FUNCTION log_consent_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Log terms consent change
    IF (TG_OP = 'UPDATE' AND OLD.consent_terms_accepted IS DISTINCT FROM NEW.consent_terms_accepted) OR
       (TG_OP = 'INSERT' AND NEW.consent_terms_accepted = TRUE) THEN
        INSERT INTO consent_history (
            user_id, consent_type, consent_given, consent_version,
            ip_address, user_agent, action
        ) VALUES (
            NEW.id, 'terms', NEW.consent_terms_accepted, NEW.consent_terms_version,
            NEW.consent_ip_address, NEW.consent_user_agent,
            CASE WHEN TG_OP = 'INSERT' THEN 'signup' ELSE 'update' END
        );
    END IF;

    -- Log privacy consent change
    IF (TG_OP = 'UPDATE' AND OLD.consent_privacy_accepted IS DISTINCT FROM NEW.consent_privacy_accepted) OR
       (TG_OP = 'INSERT' AND NEW.consent_privacy_accepted = TRUE) THEN
        INSERT INTO consent_history (
            user_id, consent_type, consent_given, consent_version,
            ip_address, user_agent, action
        ) VALUES (
            NEW.id, 'privacy', NEW.consent_privacy_accepted, NEW.consent_privacy_version,
            NEW.consent_ip_address, NEW.consent_user_agent,
            CASE WHEN TG_OP = 'INSERT' THEN 'signup' ELSE 'update' END
        );
    END IF;

    -- Log marketing consent change
    IF (TG_OP = 'UPDATE' AND OLD.consent_marketing IS DISTINCT FROM NEW.consent_marketing) OR
       (TG_OP = 'INSERT' AND NEW.consent_marketing = TRUE) THEN
        INSERT INTO consent_history (
            user_id, consent_type, consent_given, consent_version,
            ip_address, user_agent, action
        ) VALUES (
            NEW.id, 'marketing', NEW.consent_marketing, NULL,
            NEW.consent_ip_address, NEW.consent_user_agent,
            CASE WHEN TG_OP = 'INSERT' THEN 'signup' ELSE 'update' END
        );
    END IF;

    -- Log analytics consent change
    IF (TG_OP = 'UPDATE' AND OLD.consent_analytics IS DISTINCT FROM NEW.consent_analytics) OR
       (TG_OP = 'INSERT' AND NEW.consent_analytics = TRUE) THEN
        INSERT INTO consent_history (
            user_id, consent_type, consent_given, consent_version,
            ip_address, user_agent, action
        ) VALUES (
            NEW.id, 'analytics', NEW.consent_analytics, NULL,
            NEW.consent_ip_address, NEW.consent_user_agent,
            CASE WHEN TG_OP = 'INSERT' THEN 'signup' ELSE 'update' END
        );
    END IF;

    -- Log data processing consent change
    IF (TG_OP = 'UPDATE' AND OLD.consent_data_processing IS DISTINCT FROM NEW.consent_data_processing) OR
       (TG_OP = 'INSERT' AND NEW.consent_data_processing = TRUE) THEN
        INSERT INTO consent_history (
            user_id, consent_type, consent_given, consent_version,
            ip_address, user_agent, action
        ) VALUES (
            NEW.id, 'data_processing', NEW.consent_data_processing, NULL,
            NEW.consent_ip_address, NEW.consent_user_agent,
            CASE WHEN TG_OP = 'INSERT' THEN 'signup' ELSE 'update' END
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic consent logging
DROP TRIGGER IF EXISTS trigger_log_consent_change ON users;
CREATE TRIGGER trigger_log_consent_change
AFTER INSERT OR UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION log_consent_change();

-- Comments for documentation
COMMENT ON TABLE consent_history IS 'Audit log for all user consent changes (GDPR Article 7.1 requirement)';
COMMENT ON COLUMN users.consent_terms_accepted IS 'User accepted Terms of Service (required)';
COMMENT ON COLUMN users.consent_privacy_accepted IS 'User accepted Privacy Policy (required)';
COMMENT ON COLUMN users.consent_marketing IS 'User consented to marketing communications (optional, GDPR Article 6.1a)';
COMMENT ON COLUMN users.consent_analytics IS 'User consented to analytics tracking (optional)';
COMMENT ON COLUMN users.consent_data_processing IS 'User consented to AI data processing (required for service)';
COMMENT ON COLUMN users.data_retention_acknowledged IS 'User acknowledged data retention policy';
