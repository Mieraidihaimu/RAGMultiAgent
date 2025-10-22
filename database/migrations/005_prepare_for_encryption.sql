-- Migration: Prepare database for field-level encryption
-- Purpose: Convert JSONB columns to TEXT to store encrypted data
-- Date: 2025-10-22
--
-- IMPORTANT: This migration prepares the schema for encryption but does NOT encrypt existing data.
-- After running this migration, you must run the data migration script to encrypt existing data.
--
-- Encrypted Fields:
-- - users.context (JSONB -> TEXT)
-- - thoughts.text (TEXT, already correct type)
-- - thoughts.classification (JSONB -> TEXT)
-- - thoughts.analysis (JSONB -> TEXT)
-- - thoughts.value_impact (JSONB -> TEXT)
-- - thoughts.action_plan (JSONB -> TEXT)
-- - thoughts.priority (JSONB -> TEXT)
-- - thought_cache.response (JSONB -> TEXT)

-- Backup instructions:
-- Before running this migration, create a backup:
-- pg_dump -U thoughtprocessor -d thoughtprocessor > backup_before_encryption.sql

BEGIN;

-- ============================================================================
-- STEP 1: Add temporary columns for encrypted data
-- ============================================================================

-- Users table: Add temporary column for encrypted context
ALTER TABLE users
ADD COLUMN IF NOT EXISTS context_encrypted TEXT;

-- Thoughts table: Add temporary columns for encrypted analysis fields
ALTER TABLE thoughts
ADD COLUMN IF NOT EXISTS classification_encrypted TEXT,
ADD COLUMN IF NOT EXISTS analysis_encrypted TEXT,
ADD COLUMN IF NOT EXISTS value_impact_encrypted TEXT,
ADD COLUMN IF NOT EXISTS action_plan_encrypted TEXT,
ADD COLUMN IF NOT EXISTS priority_encrypted TEXT;

-- Thought cache table: Add temporary column for encrypted response
ALTER TABLE thought_cache
ADD COLUMN IF NOT EXISTS response_encrypted TEXT;

-- ============================================================================
-- STEP 2: Comments for documentation
-- ============================================================================

COMMENT ON COLUMN users.context_encrypted IS 'Encrypted user context (AES-256-GCM)';
COMMENT ON COLUMN thoughts.text IS 'Encrypted thought text (AES-256-GCM)';
COMMENT ON COLUMN thoughts.classification_encrypted IS 'Encrypted AI classification (AES-256-GCM)';
COMMENT ON COLUMN thoughts.analysis_encrypted IS 'Encrypted AI analysis (AES-256-GCM)';
COMMENT ON COLUMN thoughts.value_impact_encrypted IS 'Encrypted value impact analysis (AES-256-GCM)';
COMMENT ON COLUMN thoughts.action_plan_encrypted IS 'Encrypted action plan (AES-256-GCM)';
COMMENT ON COLUMN thoughts.priority_encrypted IS 'Encrypted priority information (AES-256-GCM)';
COMMENT ON COLUMN thought_cache.response_encrypted IS 'Encrypted cached response (AES-256-GCM)';

-- ============================================================================
-- STEP 3: Create indices for performance (on non-encrypted columns)
-- ============================================================================

-- Thoughts table: Index for common queries
CREATE INDEX IF NOT EXISTS idx_thoughts_status_created
ON thoughts(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_thoughts_user_status
ON thoughts(user_id, status);

-- ============================================================================
-- STEP 4: Create views for migration status tracking
-- ============================================================================

-- View to track migration progress
CREATE OR REPLACE VIEW encryption_migration_status AS
SELECT
    'users' AS table_name,
    'context' AS field_name,
    COUNT(*) AS total_records,
    COUNT(context_encrypted) AS encrypted_records,
    COUNT(*) - COUNT(context_encrypted) AS pending_records,
    ROUND(100.0 * COUNT(context_encrypted) / NULLIF(COUNT(*), 0), 2) AS percent_complete
FROM users
UNION ALL
SELECT
    'thoughts' AS table_name,
    'classification' AS field_name,
    COUNT(*) AS total_records,
    COUNT(classification_encrypted) AS encrypted_records,
    COUNT(classification) - COUNT(classification_encrypted) AS pending_records,
    ROUND(100.0 * COUNT(classification_encrypted) / NULLIF(COUNT(classification), 0), 2) AS percent_complete
FROM thoughts
WHERE classification IS NOT NULL
UNION ALL
SELECT
    'thoughts' AS table_name,
    'analysis' AS field_name,
    COUNT(*) AS total_records,
    COUNT(analysis_encrypted) AS encrypted_records,
    COUNT(analysis) - COUNT(analysis_encrypted) AS pending_records,
    ROUND(100.0 * COUNT(analysis_encrypted) / NULLIF(COUNT(analysis), 0), 2) AS percent_complete
FROM thoughts
WHERE analysis IS NOT NULL
UNION ALL
SELECT
    'thought_cache' AS table_name,
    'response' AS field_name,
    COUNT(*) AS total_records,
    COUNT(response_encrypted) AS encrypted_records,
    COUNT(response) - COUNT(response_encrypted) AS pending_records,
    ROUND(100.0 * COUNT(response_encrypted) / NULLIF(COUNT(response), 0), 2) AS percent_complete
FROM thought_cache
WHERE response IS NOT NULL;

-- ============================================================================
-- STEP 5: Create function to finalize migration (run after data encryption)
-- ============================================================================

CREATE OR REPLACE FUNCTION finalize_encryption_migration()
RETURNS void AS $$
BEGIN
    -- Check if all data is encrypted
    DECLARE
        pending_count INTEGER;
    BEGIN
        SELECT SUM(pending_records)::INTEGER
        INTO pending_count
        FROM encryption_migration_status;

        IF pending_count > 0 THEN
            RAISE EXCEPTION 'Cannot finalize migration: % records still pending encryption', pending_count;
        END IF;

        -- Users table: Replace context with encrypted version
        ALTER TABLE users DROP COLUMN IF EXISTS context CASCADE;
        ALTER TABLE users RENAME COLUMN context_encrypted TO context;

        -- Thoughts table: Replace analysis fields with encrypted versions
        ALTER TABLE thoughts DROP COLUMN IF EXISTS classification CASCADE;
        ALTER TABLE thoughts RENAME COLUMN classification_encrypted TO classification;

        ALTER TABLE thoughts DROP COLUMN IF EXISTS analysis CASCADE;
        ALTER TABLE thoughts RENAME COLUMN analysis_encrypted TO analysis;

        ALTER TABLE thoughts DROP COLUMN IF EXISTS value_impact CASCADE;
        ALTER TABLE thoughts RENAME COLUMN value_impact_encrypted TO value_impact;

        ALTER TABLE thoughts DROP COLUMN IF EXISTS action_plan CASCADE;
        ALTER TABLE thoughts RENAME COLUMN action_plan_encrypted TO action_plan;

        ALTER TABLE thoughts DROP COLUMN IF EXISTS priority CASCADE;
        ALTER TABLE thoughts RENAME COLUMN priority_encrypted TO priority;

        -- Thought cache: Replace response with encrypted version
        ALTER TABLE thought_cache DROP COLUMN IF EXISTS response CASCADE;
        ALTER TABLE thought_cache RENAME COLUMN response_encrypted TO response;

        RAISE NOTICE 'Encryption migration finalized successfully!';
    END;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION finalize_encryption_migration() IS
'Finalizes encryption migration by replacing original columns with encrypted versions.
Run this ONLY after all data has been encrypted using the data migration script.';

-- ============================================================================
-- STEP 6: Create rollback function (in case of issues)
-- ============================================================================

CREATE OR REPLACE FUNCTION rollback_encryption_preparation()
RETURNS void AS $$
BEGIN
    -- Remove encrypted columns
    ALTER TABLE users DROP COLUMN IF EXISTS context_encrypted;
    ALTER TABLE thoughts DROP COLUMN IF EXISTS classification_encrypted;
    ALTER TABLE thoughts DROP COLUMN IF EXISTS analysis_encrypted;
    ALTER TABLE thoughts DROP COLUMN IF EXISTS value_impact_encrypted;
    ALTER TABLE thoughts DROP COLUMN IF EXISTS action_plan_encrypted;
    ALTER TABLE thoughts DROP COLUMN IF EXISTS priority_encrypted;
    ALTER TABLE thought_cache DROP COLUMN IF EXISTS response_encrypted;

    -- Drop migration views
    DROP VIEW IF EXISTS encryption_migration_status;

    RAISE NOTICE 'Encryption preparation rolled back successfully';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION rollback_encryption_preparation() IS
'Rolls back encryption preparation by removing temporary encrypted columns.
Use this if you need to abort the encryption migration.';

COMMIT;

-- ============================================================================
-- MIGRATION INSTRUCTIONS
-- ============================================================================

-- 1. Run this migration:
--    psql -U thoughtprocessor -d thoughtprocessor -f 005_prepare_for_encryption.sql

-- 2. Generate and set encryption master key:
--    python -c 'from common.security import EncryptionService; print(EncryptionService.generate_master_key())'
--    # Add to .env: ENCRYPTION_MASTER_KEY=<generated_key>

-- 3. Run data migration script to encrypt existing data:
--    python database/migrate_encrypt_data.py

-- 4. Monitor progress:
--    psql -U thoughtprocessor -d thoughtprocessor -c "SELECT * FROM encryption_migration_status;"

-- 5. After all data is encrypted (100% complete), finalize migration:
--    psql -U thoughtprocessor -d thoughtprocessor -c "SELECT finalize_encryption_migration();"

-- 6. If issues occur and you need to rollback:
--    psql -U thoughtprocessor -d thoughtprocessor -c "SELECT rollback_encryption_preparation();"
--    # Then restore from backup:
--    psql -U thoughtprocessor -d thoughtprocessor < backup_before_encryption.sql

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check migration status:
-- SELECT * FROM encryption_migration_status;

-- Count total records to encrypt:
-- SELECT SUM(total_records) FROM encryption_migration_status;

-- Check if migration is complete:
-- SELECT
--     CASE
--         WHEN SUM(pending_records) = 0 THEN 'READY TO FINALIZE'
--         ELSE CONCAT(SUM(pending_records), ' records still pending')
--     END AS status
-- FROM encryption_migration_status;
