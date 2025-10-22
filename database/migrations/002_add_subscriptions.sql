-- Add subscription-related columns to users table
-- Migration: 002_add_subscriptions.sql

-- Add subscription columns if they don't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(50) DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_start_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_end_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_thought_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_thought_limit INTEGER DEFAULT 10;

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_subscription_id ON users(subscription_id);

-- Create subscription history table for tracking changes
CREATE TABLE IF NOT EXISTS subscription_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL, -- 'created', 'upgraded', 'downgraded', 'cancelled', 'renewed'
    old_plan VARCHAR(50),
    new_plan VARCHAR(50),
    amount_paid DECIMAL(10, 2),
    stripe_invoice_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB
);

-- Create index on subscription history
CREATE INDEX IF NOT EXISTS idx_subscription_history_user_id ON subscription_history(user_id);
CREATE INDEX IF NOT EXISTS idx_subscription_history_created_at ON subscription_history(created_at);

-- Update plan limits function
CREATE OR REPLACE FUNCTION update_plan_limits()
RETURNS TRIGGER AS $$
BEGIN
    -- Set monthly thought limits based on plan
    CASE NEW.subscription_plan
        WHEN 'free' THEN
            NEW.monthly_thought_limit := 10;
        WHEN 'pro' THEN
            NEW.monthly_thought_limit := NULL; -- unlimited
        WHEN 'enterprise' THEN
            NEW.monthly_thought_limit := NULL; -- unlimited
        ELSE
            NEW.monthly_thought_limit := 10; -- default to free
    END CASE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update limits when plan changes
DROP TRIGGER IF EXISTS trigger_update_plan_limits ON users;
CREATE TRIGGER trigger_update_plan_limits
    BEFORE INSERT OR UPDATE OF subscription_plan ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_plan_limits();

-- Function to reset monthly thought counts (run at start of each month)
CREATE OR REPLACE FUNCTION reset_monthly_thought_counts()
RETURNS void AS $$
BEGIN
    UPDATE users SET monthly_thought_count = 0;
END;
$$ LANGUAGE plpgsql;

-- Function to check if user can create a thought
CREATE OR REPLACE FUNCTION can_create_thought(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_plan VARCHAR(50);
    v_count INTEGER;
    v_limit INTEGER;
BEGIN
    SELECT subscription_plan, monthly_thought_count, monthly_thought_limit
    INTO v_plan, v_count, v_limit
    FROM users
    WHERE id = p_user_id;

    -- Unlimited plans (pro, enterprise)
    IF v_limit IS NULL THEN
        RETURN TRUE;
    END IF;

    -- Check against limit
    RETURN v_count < v_limit;
END;
$$ LANGUAGE plpgsql;

-- Update existing users to have free plan and email
UPDATE users
SET subscription_plan = 'free',
    email = 'user@example.com'
WHERE subscription_plan IS NULL;

COMMENT ON TABLE subscription_history IS 'Track all subscription changes for auditing and analytics';
COMMENT ON COLUMN users.subscription_plan IS 'Current subscription tier: free, pro, enterprise';
COMMENT ON COLUMN users.monthly_thought_limit IS 'NULL means unlimited';
