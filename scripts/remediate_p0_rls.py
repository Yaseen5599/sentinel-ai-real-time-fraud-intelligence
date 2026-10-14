#!/usr/bin/env python3
"""
Sentinel AI — Remediation for Defect P0: Tighten Row Level Security (RLS)
Removes unauthenticated 'anon' access from all financial, prediction, and triage tables.
Enforces strict authenticated and service_role access.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.database.db_client import DatabaseClient

RLS_UPDATE_SQL = """
-- 1. Ensure RLS is enabled on all tables
ALTER TABLE IF EXISTS transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fraud_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fraud_investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS confirmed_fraud_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS investigation_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cardholders ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS merchants ENABLE ROW LEVEL SECURITY;

-- 2. Drop existing overly-permissive policies that granted access to 'anon'
DROP POLICY IF EXISTS analyst_select_transactions ON transactions;
DROP POLICY IF EXISTS service_insert_transactions ON transactions;

DROP POLICY IF EXISTS analyst_select_predictions ON fraud_predictions;
DROP POLICY IF EXISTS service_insert_predictions ON fraud_predictions;

DROP POLICY IF EXISTS analyst_select_investigations ON fraud_investigations;
DROP POLICY IF EXISTS analyst_update_investigations ON fraud_investigations;
DROP POLICY IF EXISTS service_insert_investigations ON fraud_investigations;

DROP POLICY IF EXISTS analyst_select_outcomes ON confirmed_fraud_outcomes;
DROP POLICY IF EXISTS service_insert_outcomes ON confirmed_fraud_outcomes;

DROP POLICY IF EXISTS analyst_select_audit_logs ON investigation_audit_logs;
DROP POLICY IF EXISTS service_insert_audit_logs ON investigation_audit_logs;

DROP POLICY IF EXISTS auth_select_cardholders ON cardholders;
DROP POLICY IF EXISTS auth_select_merchants ON merchants;

-- 3. Create hardened policies strictly for authenticated analysts and service_role (NO anon)

-- Transactions
CREATE POLICY analyst_select_transactions ON transactions
    FOR SELECT TO authenticated, service_role
    USING (true);

CREATE POLICY service_insert_transactions ON transactions
    FOR INSERT TO authenticated, service_role
    WITH CHECK (true);

-- Fraud Predictions
CREATE POLICY analyst_select_predictions ON fraud_predictions
    FOR SELECT TO authenticated, service_role
    USING (true);

CREATE POLICY service_insert_predictions ON fraud_predictions
    FOR INSERT TO authenticated, service_role
    WITH CHECK (true);

-- Fraud Investigations
CREATE POLICY analyst_select_investigations ON fraud_investigations
    FOR SELECT TO authenticated, service_role
    USING (true);

CREATE POLICY analyst_update_investigations ON fraud_investigations
    FOR UPDATE TO authenticated, service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY service_insert_investigations ON fraud_investigations
    FOR INSERT TO authenticated, service_role
    WITH CHECK (true);

-- Confirmed Outcomes
CREATE POLICY analyst_select_outcomes ON confirmed_fraud_outcomes
    FOR SELECT TO authenticated, service_role
    USING (true);

CREATE POLICY service_insert_outcomes ON confirmed_fraud_outcomes
    FOR INSERT TO authenticated, service_role
    WITH CHECK (true);

-- Audit Logs
CREATE POLICY analyst_select_audit_logs ON investigation_audit_logs
    FOR SELECT TO authenticated, service_role
    USING (true);

CREATE POLICY service_insert_audit_logs ON investigation_audit_logs
    FOR INSERT TO authenticated, service_role
    WITH CHECK (true);

-- Reference Tables
CREATE POLICY auth_select_cardholders ON cardholders
    FOR SELECT TO authenticated, service_role
    USING (true);

CREATE POLICY auth_select_merchants ON merchants
    FOR SELECT TO authenticated, service_role
    USING (true);

-- 4. Defense-in-depth: Revoke all direct privileges on sensitive tables from anon role
REVOKE ALL ON transactions FROM anon;
REVOKE ALL ON fraud_predictions FROM anon;
REVOKE ALL ON fraud_investigations FROM anon;
REVOKE ALL ON confirmed_fraud_outcomes FROM anon;
REVOKE ALL ON investigation_audit_logs FROM anon;
REVOKE ALL ON cardholders FROM anon;
REVOKE ALL ON merchants FROM anon;
"""

def apply_rls_remediation():
    client = DatabaseClient()
    if not client.test_connection():
        print("[-] Error: Unable to connect to database.")
        sys.exit(1)
        
    print("[*] Applying tightened RLS policies to Supabase PostgreSQL...")
    with client.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(RLS_UPDATE_SQL)
        conn.commit()
    print("[+] Successfully tightened RLS policies on Supabase Cloud.")

    # Verification query
    with client.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT tablename, policyname, roles, cmd
                FROM pg_policies
                WHERE schemaname = 'public'
                ORDER BY tablename, policyname;
            ''')
            rows = cur.fetchall()
            print("\n[+] Verified Deployed Policies:")
            has_anon = False
            for r in rows:
                print(f"  - Table: {r[0]:<25} | Policy: {r[1]:<30} | Roles: {r[2]} | Cmd: {r[3]}")
                if 'anon' in r[2]:
                    has_anon = True
            
            if has_anon:
                print("[-] WARNING: 'anon' role still found in some policies!")
            else:
                print("\n[✔] Zero 'anon' policies exist. Public unauthenticated access completely revoked!")

if __name__ == "__main__":
    apply_rls_remediation()
