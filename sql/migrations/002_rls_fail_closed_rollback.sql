-- ==============================================================================
-- Sentinel AI — Migration 002: Safe Emergency Recovery Baseline
-- Security Mandate:
--   1. DO NOT RESTORE historic fail-open policies: COALESCE(..., 'fraud_investigator')
--      is strictly forbidden as it re-introduces unauthenticated data leakage.
--   2. DO NOT RESTORE permissive insert policies: WITH CHECK (true) is strictly
--      forbidden as it allows unauthenticated or unauthorized transaction forging.
--   3. This script provides a safe, restrictive rollback procedure that restores
--      operational baseline while preserving complete fail-closed authorization
--      and append-only ledger protections.
-- ==============================================================================

BEGIN;

-- 1. Transactions Policy: Safe Restrictive Baseline
DROP POLICY IF EXISTS rbac_select_transactions ON public.transactions;
CREATE POLICY rbac_select_transactions ON public.transactions
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
    OR (
        -- Customers: Strictly bound to verified server app_metadata card_id
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') = 'customer'
        AND card_id = (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'card_id')
    )
);

DROP POLICY IF EXISTS service_insert_transactions ON public.transactions;
CREATE POLICY service_insert_transactions ON public.transactions
FOR INSERT TO authenticated, service_role
WITH CHECK (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

-- 2. Fraud Predictions Policy: Safe Restrictive Baseline
DROP POLICY IF EXISTS rbac_select_predictions ON public.fraud_predictions;
CREATE POLICY rbac_select_predictions ON public.fraud_predictions
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

DROP POLICY IF EXISTS service_insert_predictions ON public.fraud_predictions;
CREATE POLICY service_insert_predictions ON public.fraud_predictions
FOR INSERT TO authenticated, service_role
WITH CHECK (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

-- 3. Fraud Investigations Policy: Safe Restrictive Baseline
DROP POLICY IF EXISTS rbac_select_investigations ON public.fraud_investigations;
CREATE POLICY rbac_select_investigations ON public.fraud_investigations
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

DROP POLICY IF EXISTS rbac_update_investigations ON public.fraud_investigations;
CREATE POLICY rbac_update_investigations ON public.fraud_investigations
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

DROP POLICY IF EXISTS service_insert_investigations ON public.fraud_investigations;
CREATE POLICY service_insert_investigations ON public.fraud_investigations
FOR INSERT TO authenticated, service_role
WITH CHECK (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

-- 4. Confirmed Fraud Outcomes Policy: Safe Restrictive Baseline
DROP POLICY IF EXISTS rbac_select_outcomes ON public.confirmed_fraud_outcomes;
CREATE POLICY rbac_select_outcomes ON public.confirmed_fraud_outcomes
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

DROP POLICY IF EXISTS service_insert_outcomes ON public.confirmed_fraud_outcomes;
CREATE POLICY service_insert_outcomes ON public.confirmed_fraud_outcomes
FOR INSERT TO authenticated, service_role
WITH CHECK (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

-- 5. Investigation Audit Logs Policy: Safe Restrictive Baseline
DROP POLICY IF EXISTS rbac_select_audit_logs ON public.investigation_audit_logs;
CREATE POLICY rbac_select_audit_logs ON public.investigation_audit_logs
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

DROP POLICY IF EXISTS service_insert_audit_logs ON public.investigation_audit_logs;
CREATE POLICY service_insert_audit_logs ON public.investigation_audit_logs
FOR INSERT TO authenticated, service_role
WITH CHECK (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator')
    )
);

-- 6. Cardholders & Merchants Reference Dimensions
DROP POLICY IF EXISTS rbac_select_cardholders ON public.cardholders;
CREATE POLICY rbac_select_cardholders ON public.cardholders
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

DROP POLICY IF EXISTS rbac_select_merchants ON public.merchants;
CREATE POLICY rbac_select_merchants ON public.merchants
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role') IN ('admin', 'fraud_investigator', 'customer')
    )
);

-- 7. Preserve Immutable Append-Only Ledger Protections
REVOKE DELETE, TRUNCATE, UPDATE ON public.transactions FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.fraud_predictions FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.confirmed_fraud_outcomes FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.investigation_audit_logs FROM authenticated;
REVOKE DELETE, TRUNCATE ON public.fraud_investigations FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.cardholders FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.merchants FROM authenticated;

COMMIT;
