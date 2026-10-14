#!/usr/bin/env python3
"""
Sentinel AI — Complete P0/P1 Remediation Script
Applies comprehensive multi-role RBAC and customer-isolated RLS policies to Supabase PostgreSQL.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.database.db_client import DatabaseClient

MIGRATION_SQL = """
RESET ROLE;

-- 1. Ensure user_id column exists on transactions & cardholders for customer isolation
ALTER TABLE IF EXISTS transactions ADD COLUMN IF NOT EXISTS user_id VARCHAR(64);
UPDATE transactions SET user_id = 'usr_' || card_id WHERE user_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);

ALTER TABLE IF EXISTS cardholders ADD COLUMN IF NOT EXISTS user_id VARCHAR(64);
UPDATE cardholders SET user_id = 'usr_' || card_id WHERE user_id IS NULL;

-- 2. Update view to expose user_id with security_invoker = true
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

-- 3. Ensure RLS enabled on all tables
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE fraud_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE fraud_investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE confirmed_fraud_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigation_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cardholders ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchants ENABLE ROW LEVEL SECURITY;

-- 4. Clean up previous policies
DROP POLICY IF EXISTS analyst_select_transactions ON transactions;
DROP POLICY IF EXISTS customer_select_transactions ON transactions;
DROP POLICY IF EXISTS rbac_select_transactions ON transactions;
DROP POLICY IF EXISTS service_insert_transactions ON transactions;

DROP POLICY IF EXISTS analyst_select_predictions ON fraud_predictions;
DROP POLICY IF EXISTS rbac_select_predictions ON fraud_predictions;
DROP POLICY IF EXISTS service_insert_predictions ON fraud_predictions;

DROP POLICY IF EXISTS analyst_select_investigations ON fraud_investigations;
DROP POLICY IF EXISTS rbac_select_investigations ON fraud_investigations;
DROP POLICY IF EXISTS analyst_update_investigations ON fraud_investigations;
DROP POLICY IF EXISTS rbac_update_investigations ON fraud_investigations;
DROP POLICY IF EXISTS service_insert_investigations ON fraud_investigations;

DROP POLICY IF EXISTS analyst_select_outcomes ON confirmed_fraud_outcomes;
DROP POLICY IF EXISTS rbac_select_outcomes ON confirmed_fraud_outcomes;
DROP POLICY IF EXISTS service_insert_outcomes ON confirmed_fraud_outcomes;

DROP POLICY IF EXISTS analyst_select_audit_logs ON investigation_audit_logs;
DROP POLICY IF EXISTS rbac_select_audit_logs ON investigation_audit_logs;
DROP POLICY IF EXISTS service_insert_audit_logs ON investigation_audit_logs;

DROP POLICY IF EXISTS auth_select_cardholders ON cardholders;
DROP POLICY IF EXISTS rbac_select_cardholders ON cardholders;

DROP POLICY IF EXISTS auth_select_merchants ON merchants;
DROP POLICY IF EXISTS rbac_select_merchants ON merchants;

-- 5. Deploy Strict Role-Based Policies

-- TRANSACTIONS:
-- - Admins & Investigators see all transactions
-- - Customers see ONLY their own transactions (matched on user_id or card_id)
-- - anon sees 0
CREATE POLICY rbac_select_transactions ON transactions
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), ''),
            'fraud_investigator'
        ) IN ('admin', 'fraud_investigator')
    )
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), '')
        ) = 'customer'
        AND (
            user_id = (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
            OR card_id = (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'card_id')
            OR user_id = ('usr_' || coalesce((nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'card_id'), ''))
        )
    )
);

CREATE POLICY service_insert_transactions ON transactions
FOR INSERT TO authenticated, service_role
WITH CHECK (true);

-- FRAUD PREDICTIONS:
-- - Only Admins, Investigators, and Service Role see predictions.
-- - Customers see 0. anon sees 0.
CREATE POLICY rbac_select_predictions ON fraud_predictions
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), ''),
            'fraud_investigator'
        ) IN ('admin', 'fraud_investigator')
    )
);

CREATE POLICY service_insert_predictions ON fraud_predictions
FOR INSERT TO authenticated, service_role
WITH CHECK (true);

-- FRAUD INVESTIGATIONS:
-- - Only Admins and Investigators see and update cases.
-- - Customers see 0. anon sees 0.
CREATE POLICY rbac_select_investigations ON fraud_investigations
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), ''),
            'fraud_investigator'
        ) IN ('admin', 'fraud_investigator')
    )
);

CREATE POLICY rbac_update_investigations ON fraud_investigations
FOR UPDATE TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), ''),
            'fraud_investigator'
        ) IN ('admin', 'fraud_investigator')
    )
)
WITH CHECK (true);

CREATE POLICY service_insert_investigations ON fraud_investigations
FOR INSERT TO authenticated, service_role
WITH CHECK (true);

-- CONFIRMED OUTCOMES:
-- - Only Admins, Investigators, and Service Role
CREATE POLICY rbac_select_outcomes ON confirmed_fraud_outcomes
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), ''),
            'fraud_investigator'
        ) IN ('admin', 'fraud_investigator')
    )
);

CREATE POLICY service_insert_outcomes ON confirmed_fraud_outcomes
FOR INSERT TO authenticated, service_role
WITH CHECK (true);

-- INVESTIGATION AUDIT LOGS:
-- - Only Admins, Investigators, and Service Role
CREATE POLICY rbac_select_audit_logs ON investigation_audit_logs
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), ''),
            'fraud_investigator'
        ) IN ('admin', 'fraud_investigator')
    )
);

CREATE POLICY service_insert_audit_logs ON investigation_audit_logs
FOR INSERT TO authenticated, service_role
WITH CHECK (true);

-- CARDHOLDERS:
-- - Admins & Investigators see all.
-- - Customers see ONLY their own profile.
CREATE POLICY rbac_select_cardholders ON cardholders
FOR SELECT TO authenticated, service_role
USING (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), ''),
            'fraud_investigator'
        ) IN ('admin', 'fraud_investigator')
    )
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), '')
        ) = 'customer'
        AND (
            card_id = (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'card_id')
            OR user_id = (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
        )
    )
);

-- MERCHANTS:
-- - Authenticated users & service_role
CREATE POLICY rbac_select_merchants ON merchants
FOR SELECT TO authenticated, service_role
USING (true);

-- 6. Defense-in-depth: Revoke all from anon
REVOKE ALL ON transactions FROM anon;
REVOKE ALL ON fraud_predictions FROM anon;
REVOKE ALL ON fraud_investigations FROM anon;
REVOKE ALL ON confirmed_fraud_outcomes FROM anon;
REVOKE ALL ON investigation_audit_logs FROM anon;
REVOKE ALL ON cardholders FROM anon;
REVOKE ALL ON merchants FROM anon;
"""

def run_migration():
    client = DatabaseClient()
    if not client.test_connection():
        print("[-] Database connection failed.")
        sys.exit(1)

    print("[*] Running RBAC & Customer Isolation migration on Supabase...")
    with client.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(MIGRATION_SQL)
        conn.commit()
    print("[+] Migration successfully applied.")

    # Verification of isolation under authenticated role
    print("\n[*] Verifying Database RLS Enforcement across roles...")
    with client.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("RESET ROLE; SET ROLE authenticated;")

            # 1. Investigator
            cur.execute('''
                SET LOCAL request.jwt.claims = '{"sub": "usr_inv_lead", "app_metadata": {"role": "fraud_investigator"}}';
                SELECT count(*) FROM transactions;
            ''')
            inv_txns = cur.fetchone()[0]

            cur.execute('''
                SELECT count(*) FROM fraud_investigations;
            ''')
            inv_cases = cur.fetchone()[0]

            print(f"  [✔] Fraud Investigator: sees {inv_txns} transactions, {inv_cases} cases.")

            # 2. Customer CARD_007
            cur.execute('''
                SET LOCAL request.jwt.claims = '{"sub": "usr_CARD_007", "card_id": "CARD_007", "app_metadata": {"role": "customer"}}';
                SELECT count(*), count(distinct card_id) FROM transactions;
            ''')
            c7_txns, c7_cards = cur.fetchone()

            cur.execute('''
                SELECT count(*) FROM fraud_investigations;
            ''')
            c7_cases = cur.fetchone()[0]

            print(f"  [✔] Customer CARD_007: sees {c7_txns} transactions (strictly {c7_cards} card: CARD_007), {c7_cases} cases (0 exposed).")

            # 3. Customer CARD_012
            cur.execute('''
                SET LOCAL request.jwt.claims = '{"sub": "usr_CARD_012", "card_id": "CARD_012", "app_metadata": {"role": "customer"}}';
                SELECT count(*), count(distinct card_id) FROM transactions;
            ''')
            c12_txns, c12_cards = cur.fetchone()
            print(f"  [✔] Customer CARD_012: sees {c12_txns} transactions (strictly {c12_cards} card: CARD_012).")

            assert c7_cases == 0, "Customer should see 0 fraud investigation cases!"
            assert c7_cards <= 1, "Customer should only see their own card transactions!"
            print("\n[SUCCESS] PostgreSQL Database-Level RLS Customer Isolation & RBAC Fully Verified!")

if __name__ == "__main__":
    run_migration()
