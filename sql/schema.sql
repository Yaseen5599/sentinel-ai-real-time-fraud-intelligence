-- ==============================================================================
-- Sentinel AI — Real-Time Financial Fraud Intelligence Database Schema
-- Architecture: Decoupled raw transactions, predictions, investigations & outcomes
-- ==============================================================================

-- 1. Cardholders baseline registry
CREATE TABLE IF NOT EXISTS cardholders (
    card_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL,
    customer_name VARCHAR(128) NOT NULL,
    home_city VARCHAR(128) NOT NULL,
    home_country VARCHAR(2) DEFAULT 'US',
    home_latitude DOUBLE PRECISION NOT NULL,
    home_longitude DOUBLE PRECISION NOT NULL,
    baseline_avg_amount NUMERIC(12, 2) DEFAULT 75.00,
    baseline_std_amount NUMERIC(12, 2) DEFAULT 35.00,
    risk_level VARCHAR(32) DEFAULT 'LOW',
    user_id VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Merchants registry
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    merchant_category_code VARCHAR(4) NOT NULL,
    category_name VARCHAR(64),
    city VARCHAR(128) NOT NULL,
    country VARCHAR(2) DEFAULT 'US',
    risk_rating DOUBLE PRECISION DEFAULT 0.05,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Raw Immutable Transactions
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(64) PRIMARY KEY,
    idempotency_key VARCHAR(128) UNIQUE,
    card_id VARCHAR(64) NOT NULL,
    merchant_id VARCHAR(64),
    merchant_name VARCHAR(128) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    channel VARCHAR(32) DEFAULT 'ONLINE_ECOMMERCE',
    city VARCHAR(128) NOT NULL,
    country VARCHAR(2) DEFAULT 'US',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    device_fingerprint VARCHAR(128),
    authorization_status VARCHAR(32) DEFAULT 'AUTHORIZED',
    user_id VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Fraud Predictions & Scorer Results (Decoupled from raw transaction)
CREATE TABLE IF NOT EXISTS fraud_predictions (
    prediction_id VARCHAR(64) PRIMARY KEY,
    transaction_id VARCHAR(64) NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    ml_score DOUBLE PRECISION NOT NULL,
    behavior_score DOUBLE PRECISION NOT NULL,
    rule_score DOUBLE PRECISION NOT NULL,
    final_fraud_score DOUBLE PRECISION NOT NULL,
    fraud_decision VARCHAR(32) NOT NULL, -- 'LEGITIMATE', 'SUSPICIOUS', 'FRAUD'
    triggered_rules JSONB DEFAULT '[]'::jsonb,
    explanation TEXT,
    processing_latency_ms DOUBLE PRECISION DEFAULT 0.0,
    model_version VARCHAR(64) DEFAULT 'canonical-rf-v1.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Fraud Investigations & Case Management (Decoupled from model predictions)
CREATE TABLE IF NOT EXISTS fraud_investigations (
    case_id VARCHAR(64) PRIMARY KEY,
    transaction_id VARCHAR(64) NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    assigned_analyst_id VARCHAR(64),
    status VARCHAR(32) DEFAULT 'OPEN', -- 'OPEN', 'UNDER_REVIEW', 'RESOLVED'
    priority VARCHAR(16) DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    analyst_decision VARCHAR(32), -- 'PENDING', 'CONFIRMED_FRAUD', 'FALSE_POSITIVE', 'SUSPICIOUS_MONITOR'
    analyst_notes TEXT,
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 6. Confirmed Fraud Outcomes (Ground Truth Feedback Loop)
CREATE TABLE IF NOT EXISTS confirmed_fraud_outcomes (
    outcome_id VARCHAR(64) PRIMARY KEY,
    transaction_id VARCHAR(64) NOT NULL UNIQUE REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    is_confirmed_fraud BOOLEAN NOT NULL,
    confirmation_source VARCHAR(64) NOT NULL, -- 'CHARGEBACK', 'BANK_ALERT', 'CARDHOLDER_REPORT', 'INVESTIGATOR'
    recovery_amount NUMERIC(12, 2) DEFAULT 0.00,
    confirmed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Audit Logs for Compliance and Investigator Actions
CREATE TABLE IF NOT EXISTS investigation_audit_logs (
    log_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) REFERENCES fraud_investigations(case_id) ON DELETE SET NULL,
    user_id VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_tx_card_id ON transactions(card_id);
CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tx_merchant ON transactions(merchant_name);
CREATE INDEX IF NOT EXISTS idx_pred_decision ON fraud_predictions(fraud_decision);
CREATE INDEX IF NOT EXISTS idx_pred_score ON fraud_predictions(final_fraud_score DESC);
CREATE INDEX IF NOT EXISTS idx_pred_tx_id ON fraud_predictions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_inv_status ON fraud_investigations(status);
CREATE INDEX IF NOT EXISTS idx_inv_priority ON fraud_investigations(priority);

-- Comprehensive Analytical View for API and Frontend (Transparent join with security_invoker)
DROP VIEW IF EXISTS v_enriched_transactions;
CREATE VIEW v_enriched_transactions WITH (security_invoker = true) AS
SELECT
    t.transaction_id,
    t.idempotency_key,
    t.card_id,
    t.user_id,
    t.amount,
    t.currency,
    t.channel,
    t.merchant_name AS merchant,
    t.city AS location,
    t.latitude,
    t.longitude,
    t.timestamp,
    t.authorization_status,
    p.prediction_id,
    p.ml_score,
    p.behavior_score,
    p.rule_score,
    p.final_fraud_score,
    p.fraud_decision,
    p.triggered_rules,
    p.explanation,
    p.processing_latency_ms,
    p.model_version,
    i.case_id,
    i.status AS investigation_status,
    i.priority AS investigation_priority,
    i.analyst_decision,
    o.is_confirmed_fraud,
    o.confirmation_source
FROM transactions t
LEFT JOIN fraud_predictions p ON t.transaction_id = p.transaction_id
LEFT JOIN fraud_investigations i ON t.transaction_id = i.transaction_id
LEFT JOIN confirmed_fraud_outcomes o ON t.transaction_id = o.transaction_id;

-- ==============================================================================
-- Row Level Security (RLS) & Multi-Role RBAC Policies (Supabase Compatible)
-- Enforces customer data isolation, investigator review, and administrative oversight.
-- ==============================================================================

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE fraud_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE fraud_investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE confirmed_fraud_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigation_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cardholders ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchants ENABLE ROW LEVEL SECURITY;

-- 1. Transactions Policy
-- Admins & Investigators see all transactions. Customers see ONLY their own records.
DO $$
BEGIN
    DROP POLICY IF EXISTS rbac_select_transactions ON transactions;
    CREATE POLICY rbac_select_transactions ON transactions
    FOR SELECT TO authenticated, service_role
    USING (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') = 'customer'
            AND card_id = (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'card_id')
        )
    );

    DROP POLICY IF EXISTS service_insert_transactions ON transactions;
    CREATE POLICY service_insert_transactions ON transactions
    FOR INSERT TO authenticated, service_role
    WITH CHECK (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );
END $$;

-- 2. Fraud Predictions Policy (Restricted to internal investigator / admin / service_role)
DO $$
BEGIN
    DROP POLICY IF EXISTS rbac_select_predictions ON fraud_predictions;
    CREATE POLICY rbac_select_predictions ON fraud_predictions
    FOR SELECT TO authenticated, service_role
    USING (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );

    DROP POLICY IF EXISTS service_insert_predictions ON fraud_predictions;
    CREATE POLICY service_insert_predictions ON fraud_predictions
    FOR INSERT TO authenticated, service_role
    WITH CHECK (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );
END $$;

-- 3. Fraud Investigations Policy (Restricted to investigator / admin / service_role)
DO $$
BEGIN
    DROP POLICY IF EXISTS rbac_select_investigations ON fraud_investigations;
    CREATE POLICY rbac_select_investigations ON fraud_investigations
    FOR SELECT TO authenticated, service_role
    USING (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );

    DROP POLICY IF EXISTS rbac_update_investigations ON fraud_investigations;
    CREATE POLICY rbac_update_investigations ON fraud_investigations
    FOR UPDATE TO authenticated, service_role
    USING (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    )
    WITH CHECK (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );

    DROP POLICY IF EXISTS service_insert_investigations ON fraud_investigations;
    CREATE POLICY service_insert_investigations ON fraud_investigations
    FOR INSERT TO authenticated, service_role
    WITH CHECK (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );
END $$;

-- 4. Confirmed Outcomes Policy
DO $$
BEGIN
    DROP POLICY IF EXISTS rbac_select_outcomes ON confirmed_fraud_outcomes;
    CREATE POLICY rbac_select_outcomes ON confirmed_fraud_outcomes
    FOR SELECT TO authenticated, service_role
    USING (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );

    DROP POLICY IF EXISTS service_insert_outcomes ON confirmed_fraud_outcomes;
    CREATE POLICY service_insert_outcomes ON confirmed_fraud_outcomes
    FOR INSERT TO authenticated, service_role
    WITH CHECK (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );
END $$;

-- 5. Investigation Audit Logs Policy
DO $$
BEGIN
    DROP POLICY IF EXISTS rbac_select_audit_logs ON investigation_audit_logs;
    CREATE POLICY rbac_select_audit_logs ON investigation_audit_logs
    FOR SELECT TO authenticated, service_role
    USING (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );

    DROP POLICY IF EXISTS service_insert_audit_logs ON investigation_audit_logs;
    CREATE POLICY service_insert_audit_logs ON investigation_audit_logs
    FOR INSERT TO authenticated, service_role
    WITH CHECK (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
    );
END $$;

-- 6. Cardholders & Merchants Reference Policies
DO $$
BEGIN
    DROP POLICY IF EXISTS rbac_select_cardholders ON cardholders;
    CREATE POLICY rbac_select_cardholders ON cardholders
    FOR SELECT TO authenticated, service_role
    USING (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
        )
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') = 'customer'
            AND card_id = (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'card_id')
        )
    );

    DROP POLICY IF EXISTS rbac_select_merchants ON merchants;
    CREATE POLICY rbac_select_merchants ON merchants
    FOR SELECT TO authenticated, service_role
    USING (
        current_user = 'service_role' OR current_user = 'postgres'
        OR (
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator', 'customer')
        )
    );
END $$;

-- 7. Defense-in-depth: Explicitly revoke all privileges from anon
REVOKE ALL ON transactions FROM anon;
REVOKE ALL ON fraud_predictions FROM anon;
REVOKE ALL ON fraud_investigations FROM anon;
REVOKE ALL ON confirmed_fraud_outcomes FROM anon;
REVOKE ALL ON investigation_audit_logs FROM anon;
REVOKE ALL ON cardholders FROM anon;
REVOKE ALL ON merchants FROM anon;
REVOKE ALL ON v_enriched_transactions FROM anon;
REVOKE ALL ON v_enriched_transactions FROM public;
GRANT SELECT ON v_enriched_transactions TO authenticated, service_role;

-- 8. Principle of Least Privilege: Revoke destructive DML on financial ledger tables
REVOKE DELETE, TRUNCATE, UPDATE ON transactions FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON fraud_predictions FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON confirmed_fraud_outcomes FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON investigation_audit_logs FROM authenticated;
REVOKE DELETE, TRUNCATE ON fraud_investigations FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON cardholders FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON merchants FROM authenticated;

-- Safe explicit grants for authenticated users
GRANT SELECT ON transactions TO authenticated;
GRANT SELECT ON fraud_predictions TO authenticated;
GRANT SELECT, UPDATE ON fraud_investigations TO authenticated;
GRANT SELECT ON confirmed_fraud_outcomes TO authenticated;
GRANT SELECT ON investigation_audit_logs TO authenticated;
GRANT SELECT ON cardholders TO authenticated;
GRANT SELECT ON merchants TO authenticated;


