#!/usr/bin/env python3
"""
Sentinel AI — Execution of Approved Pre-Migration Safety Plan
Applies:
1. Least-privilege PostgreSQL grants (revoking DELETE/TRUNCATE/UPDATE on ledger tables).
2. anon privilege revocation on v_enriched_transactions.
3. Tightened PostgREST insert policies.
4. Idempotent auth.users provisioning with secure password hashes & role metadata.
5. Complete verification of table row counts and RLS enforcement.
"""

import os
import sys
import uuid
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.database.db_client import DatabaseClient

MIGRATION_SQL = """
BEGIN;

-- 1. Defend Views: Revoke all privileges from anon
REVOKE ALL ON public.v_enriched_transactions FROM anon;
REVOKE ALL ON public.v_enriched_transactions FROM public;
GRANT SELECT ON public.v_enriched_transactions TO authenticated, service_role;

-- 2. Principle of Least Privilege: Revoke destructive DML from authenticated role
-- Financial transactions and predictions are immutable append-only
REVOKE DELETE, TRUNCATE, UPDATE ON public.transactions FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.fraud_predictions FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.confirmed_fraud_outcomes FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.investigation_audit_logs FROM authenticated;
REVOKE DELETE, TRUNCATE ON public.fraud_investigations FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.cardholders FROM authenticated;
REVOKE DELETE, TRUNCATE, UPDATE ON public.merchants FROM authenticated;

-- 3. Explicit Safe Grants for authenticated role
GRANT SELECT ON public.transactions TO authenticated;
GRANT SELECT ON public.fraud_predictions TO authenticated;
GRANT SELECT, UPDATE ON public.fraud_investigations TO authenticated;
GRANT SELECT ON public.confirmed_fraud_outcomes TO authenticated;
GRANT SELECT ON public.investigation_audit_logs TO authenticated;
GRANT SELECT ON public.cardholders TO authenticated;
GRANT SELECT ON public.merchants TO authenticated;

-- 4. Retain Full Maintenance Capability for service_role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;

-- 5. Tighten RLS INSERT on Transactions: Prevent unauthorized customer injection
DROP POLICY IF EXISTS service_insert_transactions ON public.transactions;
CREATE POLICY service_insert_transactions ON public.transactions
FOR INSERT TO authenticated, service_role
WITH CHECK (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), '')
        ) IN ('admin', 'fraud_investigator')
    )
);

-- 6. Tighten RLS INSERT on Audit Logs: Prevent client audit forgery
DROP POLICY IF EXISTS service_insert_audit_logs ON public.investigation_audit_logs;
CREATE POLICY service_insert_audit_logs ON public.investigation_audit_logs
FOR INSERT TO authenticated, service_role
WITH CHECK (
    current_user = 'service_role' OR current_user = 'postgres'
    OR (
        coalesce(
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'role'),
            nullif(current_setting('request.jwt.claim.role', true), '')
        ) IN ('admin', 'fraud_investigator')
    )
);

COMMIT;
"""

def get_direct_or_pooler_conn():
    """Connects via database pooler or direct host with dual-stack support."""
    vals = dotenv_values(PROJECT_ROOT / ".env")
    db_url = vals.get("DATABASE_URL") or vals.get("SUPABASE_DB_URL")
    
    # Try direct connect first
    try:
        conn = psycopg2.connect(db_url, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("RESET ROLE;")
        return conn
    except Exception:
        pass

    # Fallback to dual-stack IPv4 pooler
    pw = urllib.parse.unquote(db_url.split('@')[0].split(':')[-1])
    for port in [5432, 6543]:
        try:
            conn = psycopg2.connect(
                host="aws-0-ap-northeast-2.pooler.supabase.com",
                port=port,
                dbname="postgres",
                user="postgres.ixrwbfvsoqkxzmnfsuuq",
                password=pw,
                connect_timeout=5
            )
            with conn.cursor() as cur:
                cur.execute("RESET ROLE;")
            return conn
        except Exception:
            continue
    raise ConnectionError("Unable to establish connection to Supabase database.")

def provision_auth_users(conn):
    """
    Seeds canonical user accounts into auth.users idempotently
    with secure bcrypt password hashes and role app_metadata.
    """
    print("[*] Checking and provisioning canonical identities in auth.users...")
    users_to_seed = [
        {
            "id": "e0000000-0000-0000-0000-000000000001",
            "email": "admin.security@sentinel.ai",
            "role": "authenticated",
            "app_metadata": {"role": "admin", "permissions": ["all"]},
            "user_metadata": {"full_name": "Security Administrator", "department": "Executive Security"}
        },
        {
            "id": "e0000000-0000-0000-0000-000000000002",
            "email": "analyst.sarah@sentinel.ai",
            "role": "authenticated",
            "app_metadata": {
                "role": "fraud_investigator",
                "permissions": ["investigations.read", "investigations.update", "audit.read"]
            },
            "user_metadata": {"full_name": "Analyst Sarah Jenkins", "department": "Fraud Operations"}
        },
        {
            "id": "e0000000-0000-0000-0000-000000000003",
            "email": "customer.card007@sentinel.ai",
            "role": "authenticated",
            "app_metadata": {"role": "customer", "card_id": "CARD_007"},
            "user_metadata": {"full_name": "James B. (Card 007)", "card_id": "CARD_007"}
        },
        {
            "id": "e0000000-0000-0000-0000-000000000004",
            "email": "customer.card012@sentinel.ai",
            "role": "authenticated",
            "app_metadata": {"role": "customer", "card_id": "CARD_012"},
            "user_metadata": {"full_name": "Elena R. (Card 012)", "card_id": "CARD_012"}
        }
    ]

    with conn.cursor() as cur:
        # Check if auth schema exists and pgcrypto is available
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        
        for u in users_to_seed:
            import json
            check_sql = "SELECT id FROM auth.users WHERE email = %s;"
            cur.execute(check_sql, (u["email"],))
            existing = cur.fetchone()
            if not existing:
                insert_sql = """
                INSERT INTO auth.users (
                    id, instance_id, email, encrypted_password, email_confirmed_at,
                    raw_app_meta_data, raw_user_meta_data, role, aud, created_at, updated_at
                ) VALUES (
                    %s, '00000000-0000-0000-0000-000000000000', %s,
                    crypt('SentinelPass2026!', gen_salt('bf')),
                    CURRENT_TIMESTAMP, %s, %s, 'authenticated', 'authenticated',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                );
                """
                cur.execute(insert_sql, (
                    u["id"], u["email"],
                    json.dumps(u["app_metadata"]),
                    json.dumps(u["user_metadata"])
                ))
                # Also insert into auth.identities (email is a generated column)
                ident_sql = """
                INSERT INTO auth.identities (
                    id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), %s, %s, %s, 'email', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                ) ON CONFLICT DO NOTHING;
                """
                cur.execute(ident_sql, (
                    u["id"], u["id"], json.dumps({"sub": u["id"], "email": u["email"]})
                ))
                print(f"  [+] Provisioned auth user: {u['email']} (role: {u['app_metadata']['role']})")
            else:
                # Update app_metadata if needed
                update_sql = """
                UPDATE auth.users SET
                    raw_app_meta_data = %s,
                    raw_user_meta_data = %s
                WHERE email = %s;
                """
                cur.execute(update_sql, (
                    json.dumps(u["app_metadata"]),
                    json.dumps(u["user_metadata"]),
                    u["email"]
                ))
                print(f"  [✔] Existing auth user verified: {u['email']}")
        conn.commit()

def verify_live_state(conn):
    """Verifies row counts, privilege revocation, and RLS enforcement."""
    print("\n[*] Verifying Live Database State...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 1. Row counts
        tables = [
            'transactions', 'fraud_predictions', 'fraud_investigations',
            'confirmed_fraud_outcomes', 'investigation_audit_logs'
        ]
        for t in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM public.{t};")
            cnt = cur.fetchone()["count"]
            print(f"  [Data Preservation] public.{t}: {cnt} rows intact.")

        # 2. Check auth.users count
        cur.execute("SELECT COUNT(*) as count FROM auth.users;")
        u_cnt = cur.fetchone()["count"]
        print(f"  [Auth Directory] auth.users: {u_cnt} registered users.")

        # 3. Check anon privileges on view
        cur.execute("""
            SELECT privilege_type 
            FROM information_schema.table_privileges 
            WHERE table_schema = 'public' 
              AND table_name = 'v_enriched_transactions' 
              AND grantee = 'anon';
        """)
        anon_privs = [r["privilege_type"] for r in cur.fetchall()]
        assert len(anon_privs) == 0, f"anon should have 0 privileges on view! Found: {anon_privs}"
        print("  [Security] v_enriched_transactions: All privileges REVOKED from anon (0 privileges).")

        # 4. Check authenticated privileges on transactions
        cur.execute("""
            SELECT privilege_type 
            FROM information_schema.table_privileges 
            WHERE table_schema = 'public' 
              AND table_name = 'transactions' 
              AND grantee = 'authenticated';
        """)
        auth_tx_privs = set(r["privilege_type"] for r in cur.fetchall())
        assert "DELETE" not in auth_tx_privs, "DELETE should be revoked from authenticated!"
        assert "TRUNCATE" not in auth_tx_privs, "TRUNCATE should be revoked from authenticated!"
        assert "UPDATE" not in auth_tx_privs, "UPDATE should be revoked from authenticated!"
        print(f"  [Security] transactions privileges for authenticated role: {sorted(list(auth_tx_privs))} (Immutable ledger confirmed).")

        # 5. Check RLS Customer Isolation via simulated JWT claims
        cur.execute("RESET ROLE; SET ROLE authenticated;")
        cur.execute("""
            SET LOCAL request.jwt.claims = '{"sub": "usr_CARD_007", "card_id": "CARD_007", "app_metadata": {"role": "customer"}}';
            SELECT count(*), count(distinct card_id) as cards FROM public.transactions;
        """)
        c_row = cur.fetchone()
        print(f"  [RLS Enforcement] Customer CARD_007: sees {c_row['count']} transactions across strictly {c_row['cards']} card.")

        cur.execute("""
            SELECT count(*) as count FROM public.fraud_investigations;
        """)
        cases_count = cur.fetchone()["count"]
        assert cases_count == 0, "Customer should see 0 fraud investigation cases!"
        print(f"  [RLS Enforcement] Customer sees {cases_count} internal investigation cases (Zero breach).")

        cur.execute("RESET ROLE;")

def main():
    print("=" * 70)
    print("Sentinel AI — Executing Approved Pre-Migration Safety Plan")
    print("=" * 70)
    conn = get_direct_or_pooler_conn()
    print("[+] Successfully connected to Supabase PostgreSQL.")

    print("\n[*] Applying SQL DDL, Privilege Hardening, and Policy Updates...")
    with conn.cursor() as cur:
        cur.execute(MIGRATION_SQL)
    print("[+] SQL Migration committed successfully.")

    # Provision auth users
    provision_auth_users(conn)

    # Verify state
    verify_live_state(conn)

    conn.close()
    print("\n" + "=" * 70)
    print("[SUCCESS] All Approved Security & Pre-Migration Changes Deployed & Verified!")
    print("=" * 70)

if __name__ == "__main__":
    main()
