-- ==============================================================================
-- Migration 003: Customer Authorization Workflow & Deterministic Ordering
-- 
-- Rationale:
-- 1. Sets default authorization_status for transactions to 'PENDING'.
--    Newly created transactions must remain 'PENDING' until explicitly approved
--    by an authenticated administrator or fraud investigator.
-- 2. Adds authorized_by and authorized_at audit fields to transactions table.
-- 3. Updates analytical view v_enriched_transactions to include ingested_at,
--    authorized_by, and authorized_at for newest-first deterministic querying.
-- 4. Creates performance indexes on ingested_at and opened_at.
-- ==============================================================================

-- 1. Default authorization_status to 'PENDING'
ALTER TABLE transactions ALTER COLUMN authorization_status SET DEFAULT 'PENDING';

-- 2. Add audit fields for authorized transactions
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS authorized_by VARCHAR(64);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS authorized_at TIMESTAMP WITH TIME ZONE;

-- 3. Performance indexes for server-side newest-first ordering
CREATE INDEX IF NOT EXISTS idx_tx_ingested_at ON transactions(ingested_at DESC);
CREATE INDEX IF NOT EXISTS idx_tx_timestamp_tx_id ON transactions(timestamp DESC, transaction_id DESC);
CREATE INDEX IF NOT EXISTS idx_inv_opened_at_case_id ON fraud_investigations(opened_at DESC, case_id DESC);

-- 4. Recreate enriched transactions view with audit columns and ingested_at
DROP VIEW IF EXISTS v_enriched_transactions CASCADE;
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
    t.merchant_name,
    t.city AS location,
    t.city,
    t.latitude,
    t.longitude,
    t.timestamp,
    t.authorization_status,
    t.authorized_by,
    t.authorized_at,
    t.ingested_at,
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
