-- ==============================================================================
-- Sentinel AI — Migration 002: RLS Fail-Closed Hardening
-- Priority: P0 Critical Security Remediation
-- Objective:
--   1. Eliminate all privileged COALESCE fallbacks (no default to fraud_investigator).
--   2. Ensure missing, null, empty, or malformed claims fail closed (return 0 rows).
--   3. Bind customer access strictly to verified app_metadata identity and card_id.
--   4. Preserve immutable append-only ledger permissions.
-- ==============================================================================

BEGIN;

-- Set a strict lock timeout to prevent queueing or indefinite blocking
SET LOCAL lock_timeout = '5s';

-- 1. Transactions Policy (Fail-Closed Customer & Investigator RBAC)
DROP POLICY IF EXISTS rbac_select_transactions ON public.transactions;
CREATE POLICY rbac_select_transactions ON public.transactions
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        -- Investigators and Admins: Verified explicitly in server app_metadata
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

-- 2. Fraud Predictions Policy (Fail-Closed: Internal Investigators & Admins Only)
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

-- 3. Fraud Investigations Policy (Fail-Closed: Triage & Updates restricted to Investigators & Admins)
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

-- 4. Confirmed Fraud Outcomes Policy (Fail-Closed)
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

-- 5. Investigation Audit Logs Policy (Fail-Closed: Strict Admin & Investigator Oversight)
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
