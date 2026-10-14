"""
Sentinel AI — Security Remediation Regression Test Suite
Validates P0/P1 security fixes:
A. Missing token (401 Unauthorized)
B. Invalid signature (401 Unauthorized)
C. Expired token (401 Unauthorized)
D. Wrong issuer (401 Unauthorized)
E. Wrong audience (401 Unauthorized)
F. Role self-assignment prevention (403 Forbidden)
G. Missing role claim (Fail-closed: 403 Forbidden)
H. Empty role claim (Fail-closed: 403 Forbidden)
I. Invalid role claim (Fail-closed: 403 Forbidden)
J. Customer attempts to access another customer's transactions (403 Forbidden)
K. Customer attempts to access investigation endpoints (403 Forbidden)
L. Investigator attempts administrator-only operations (403 Forbidden)
M. Legitimate investigator and administrator workflows (200 OK)
N. Database writes remain functional for authorized workflows (201/200 OK)
O. Append-only protections remain effective (PostgreSQL Kernel Privilege Denied)
"""

import pytest
import jwt
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from src.api.main import (
    app,
    SUPABASE_JWT_SECRET,
    ALGORITHM,
    SUPABASE_ISSUER,
    SUPABASE_AUDIENCE,
    create_access_token
)
from src.database.db_client import DatabaseClient

client = TestClient(app)

def make_test_token(
    sub="usr_test",
    email="test@sentinel.ai",
    role="fraud_investigator",
    card_id=None,
    issuer=SUPABASE_ISSUER,
    audience=SUPABASE_AUDIENCE,
    secret=SUPABASE_JWT_SECRET,
    expired=False,
    include_role_in_app_meta=True,
    app_meta_role="fraud_investigator"
):
    now = datetime.now(timezone.utc)
    exp = (now - timedelta(hours=1)) if expired else (now + timedelta(hours=2))
    app_metadata = {}
    if include_role_in_app_meta:
        app_metadata["role"] = app_meta_role
    if card_id:
        app_metadata["card_id"] = card_id

    payload = {
        "sub": sub,
        "email": email,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "iss": issuer,
        "aud": audience,
        "app_metadata": app_metadata
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

# ------------------------------------------------------------------------------
# Test A: Missing Token
# ------------------------------------------------------------------------------
def test_a_missing_token():
    resp = client.get("/api/v1/cases")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]

# ------------------------------------------------------------------------------
# Test B: Invalid Signature
# ------------------------------------------------------------------------------
def test_b_invalid_signature():
    bad_token = make_test_token(secret="completely_wrong_secret_key_123456789")
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {bad_token}"})
    assert resp.status_code == 401
    assert "signature" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()

# ------------------------------------------------------------------------------
# Test C: Expired Token
# ------------------------------------------------------------------------------
def test_c_expired_token():
    exp_token = make_test_token(expired=True)
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {exp_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()

# ------------------------------------------------------------------------------
# Test D: Wrong Issuer
# ------------------------------------------------------------------------------
def test_d_wrong_issuer():
    wrong_iss_token = make_test_token(issuer="https://evil-untrusted-issuer.attacker.com/auth/v1")
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {wrong_iss_token}"})
    assert resp.status_code == 401
    assert "issuer" in resp.json()["detail"].lower()

# ------------------------------------------------------------------------------
# Test E: Wrong Audience
# ------------------------------------------------------------------------------
def test_e_wrong_audience():
    wrong_aud_token = make_test_token(audience="malicious_audience")
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {wrong_aud_token}"})
    assert resp.status_code == 401
    assert "audience" in resp.json()["detail"].lower()

# ------------------------------------------------------------------------------
# Test F: Role Self-Assignment Prevention
# ------------------------------------------------------------------------------
def test_f_role_self_assignment_prevention():
    # Customer Alice attempts to self-assign the 'admin' role
    resp = client.post("/api/v1/auth/login", json={
        "email": "customer.alice@bank.com",
        "password": "SentinelPass2026!",
        "role": "admin"
    })
    # Must reject privilege escalation attempt
    assert resp.status_code == 403
    assert "self-assign" in resp.json()["detail"].lower()

# ------------------------------------------------------------------------------
# Test G: Missing Role Claim (Fail-Closed)
# ------------------------------------------------------------------------------
def test_g_missing_role_claim():
    token_no_role = make_test_token(include_role_in_app_meta=False)
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_no_role}"})
    assert resp.status_code == 403
    assert "Access forbidden" in resp.json()["detail"]

# ------------------------------------------------------------------------------
# Test H: Empty Role Claim (Fail-Closed)
# ------------------------------------------------------------------------------
def test_h_empty_role_claim():
    token_empty_role = make_test_token(app_meta_role="")
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_empty_role}"})
    assert resp.status_code == 403
    assert "Access forbidden" in resp.json()["detail"]

# ------------------------------------------------------------------------------
# Test I: Invalid Role Claim (Fail-Closed)
# ------------------------------------------------------------------------------
def test_i_invalid_role_claim():
    token_inv = make_test_token(app_meta_role="unauthorized_attacker")
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_inv}"})
    assert resp.status_code == 403
    assert "unauthorized_attacker" in resp.json()["detail"]

# ------------------------------------------------------------------------------
# Test J: Customer Attempts Cross-Customer Transaction Access
# ------------------------------------------------------------------------------
def test_j_customer_cross_access_isolation():
    # Alice is assigned CARD_007
    alice_login = client.post("/api/v1/auth/login", json={
        "email": "customer.alice@bank.com",
        "password": "SentinelPass2026!"
    })
    assert alice_login.status_code == 200
    token = alice_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Alice views CARD_007 -> 200 OK
    own_resp = client.get("/api/v1/customer/transactions", headers=headers)
    assert own_resp.status_code == 200

    # Alice tries to view Bob's CARD_012 -> 403 Forbidden
    cross_resp = client.get("/api/v1/customer/transactions?card_id=CARD_012", headers=headers)
    assert cross_resp.status_code == 403
    assert "Forbidden" in cross_resp.json()["detail"]

# ------------------------------------------------------------------------------
# Test K: Customer Attempts Access to Investigation Endpoints
# ------------------------------------------------------------------------------
def test_k_customer_investigation_boundary():
    alice_login = client.post("/api/v1/auth/login", json={
        "email": "customer.alice@bank.com",
        "password": "SentinelPass2026!"
    })
    token = alice_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access cases -> 403 Forbidden
    assert client.get("/api/v1/cases", headers=headers).status_code == 403
    # Access KPIs -> 403 Forbidden
    assert client.get("/api/v1/analytics/kpis", headers=headers).status_code == 403
    # Access raw transaction stream -> 403 Forbidden
    assert client.get("/api/v1/transactions/recent", headers=headers).status_code == 403

# ------------------------------------------------------------------------------
# Test L: Investigator Attempts Administrator-Only Operations
# ------------------------------------------------------------------------------
def test_l_investigator_admin_boundary():
    sarah_login = client.post("/api/v1/auth/login", json={
        "email": "analyst.sarah@sentinel.ai",
        "password": "SentinelPass2026!"
    })
    assert sarah_login.status_code == 200
    token = sarah_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Investigator views cases -> 200 OK
    assert client.get("/api/v1/cases", headers=headers).status_code == 200
    # Investigator accesses Admin audit logs -> 403 Forbidden
    resp = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert resp.status_code == 403
    assert "Access forbidden" in resp.json()["detail"]

# ------------------------------------------------------------------------------
# Test M: Legitimate Investigator and Administrator Workflows
# ------------------------------------------------------------------------------
def test_m_legitimate_investigator_and_admin_workflows():
    # 1. Admin login
    admin_login = client.post("/api/v1/auth/login", json={
        "email": "admin.security@sentinel.ai",
        "password": "SentinelPass2026!"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin reads audit logs
    audit_resp = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    assert isinstance(audit_resp.json(), list)

    # 2. Investigator reads cases & KPIs
    sarah_login = client.post("/api/v1/auth/login", json={
        "email": "analyst.sarah@sentinel.ai",
        "password": "SentinelPass2026!"
    })
    inv_token = sarah_login.json()["access_token"]
    inv_headers = {"Authorization": f"Bearer {inv_token}"}

    assert client.get("/api/v1/cases", headers=inv_headers).status_code == 200
    assert client.get("/api/v1/analytics/kpis", headers=inv_headers).status_code == 200

# ------------------------------------------------------------------------------
# Test N: Authorized Database Writes Remain Functional
# ------------------------------------------------------------------------------
def test_n_authorized_database_writes_functional():
    # Ingestion endpoint operates via gateway with verified authorization
    token = make_test_token(sub="usr_auth_ingest", app_meta_role="fraud_investigator")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "card_id": "CARD_007",
        "amount": 55.00,
        "merchant_name": "Target",
        "merchant_category_code": "5311",
        "city": "Chicago",
        "channel": "IN_PERSON_CHIP"
    }
    ingest_resp = client.post("/api/v1/transactions", json=payload, headers=headers)
    assert ingest_resp.status_code == 201
    assert ingest_resp.json()["status"] == "processed"

# ------------------------------------------------------------------------------
# Test O: Append-Only Protections Effective (Actual PostgreSQL Kernel Verification)
# ------------------------------------------------------------------------------
def test_o_append_only_protections_effective():
    db = DatabaseClient()
    if not db.test_connection():
        pytest.skip("Supabase PostgreSQL is offline; skipping kernel privilege test.")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("RESET ROLE; SET ROLE authenticated;")
            
            # 1. Test DELETE on transactions is blocked
            try:
                cur.execute("DELETE FROM public.transactions WHERE transaction_id = 'TX_NONEXISTENT';")
                pytest.fail("Security violation: authenticated role was able to DELETE from transactions!")
            except Exception as e:
                conn.rollback()
                assert "permission denied" in str(e).lower()

            # 2. Test TRUNCATE on transactions is blocked
            with conn.cursor() as cur2:
                cur2.execute("RESET ROLE; SET ROLE authenticated;")
                try:
                    cur2.execute("TRUNCATE public.transactions;")
                    pytest.fail("Security violation: authenticated role was able to TRUNCATE transactions!")
                except Exception as e:
                    conn.rollback()
                    assert "permission denied" in str(e).lower()

            # 3. Test DELETE on investigation_audit_logs is blocked
            with conn.cursor() as cur3:
                cur3.execute("RESET ROLE; SET ROLE authenticated;")
                try:
                    cur3.execute("DELETE FROM public.investigation_audit_logs;")
                    pytest.fail("Security violation: authenticated role was able to DELETE from investigation_audit_logs!")
                except Exception as e:
                    conn.rollback()
                    assert "permission denied" in str(e).lower()

# ------------------------------------------------------------------------------
# Test P: Unknown Email & Unauthenticated Token Minting Prevention
# ------------------------------------------------------------------------------
def test_p_unknown_email_and_token_minting_prevention():
    # 1. Unregistered email with arbitrary password must be rejected with 401
    resp = client.post("/api/v1/auth/login", json={
        "email": "intruder.unregistered@attacker.com",
        "password": "ArbitraryPassword2026!"
    })
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]

    # 2. Unregistered email attempting to claim CARD_007 must NOT mint a token
    exploit_resp = client.post("/api/v1/auth/login", json={
        "email": "stranger.attacker@evil.org",
        "password": "AnyRandomPassword123!",
        "card_id": "CARD_007"
    })
    assert exploit_resp.status_code == 401
    assert "Invalid email or password" in exploit_resp.json()["detail"]

# ------------------------------------------------------------------------------
# Test Q: Invalid or Missing Password Rejection
# ------------------------------------------------------------------------------
def test_q_invalid_or_missing_password_rejected():
    # 1. Known user with wrong password -> 401 Unauthorized
    resp_bad_pw = client.post("/api/v1/auth/login", json={
        "email": "customer.card007@sentinel.ai",
        "password": "WrongPasswordAttempt123!"
    })
    assert resp_bad_pw.status_code == 401
    assert "Invalid email or password" in resp_bad_pw.json()["detail"]

    # 2. Too short / empty password -> 400 Bad Request
    resp_short = client.post("/api/v1/auth/login", json={
        "email": "customer.card007@sentinel.ai",
        "password": "123"
    })
    assert resp_short.status_code == 400

# ------------------------------------------------------------------------------
# Test R: Customer Identity Lacking Card Binding Fails Closed
# ------------------------------------------------------------------------------
def test_r_customer_lacking_card_binding_fails_closed():
    # Token has verified role 'customer', but NO card_id in app_metadata
    unbound_customer_token = make_test_token(
        sub="usr_unbound_cust",
        email="unbound.customer@newbank.com",
        app_meta_role="customer",
        card_id=None
    )
    headers = {"Authorization": f"Bearer {unbound_customer_token}"}

    # Attempting to access customer transactions must NOT fallback to CARD_007; must be 403 Forbidden
    resp = client.get("/api/v1/customer/transactions", headers=headers)
    assert resp.status_code == 403
    assert "lacks an authorized card binding" in resp.json()["detail"].lower()

# ------------------------------------------------------------------------------
# Test S: Rollback Script Security Properties Verification
# ------------------------------------------------------------------------------
def test_s_rollback_script_security_properties():
    with open("sql/migrations/002_rls_fail_closed_rollback.sql", "r") as f:
        code_lines = [line.strip().lower() for line in f if not line.strip().startswith("--")]
        code_sql = " ".join(code_lines)

    # Must NOT restore fail-open coalesce fallback
    assert "fraud_investigator" not in code_sql or "app_metadata" in code_sql
    assert "with check (true)" not in code_sql, "Rollback script must not allow unrestricted WITH CHECK (true) inserts!"
    assert "revoke delete, truncate, update on public.transactions from authenticated" in code_sql
    assert "revoke delete, truncate on public.fraud_investigations from authenticated" in code_sql

# ------------------------------------------------------------------------------
# Test T: Merchant Policy Explicit Role Validation
# ------------------------------------------------------------------------------
def test_t_merchant_policy_role_validation():
    db = DatabaseClient()
    if not db.test_connection():
        pytest.skip("Database connection unavailable")

    # 1. Missing claims -> fails closed
    r_missing = db.execute_with_rls_context(claims={}, query_sql="SELECT count(*) FROM public.merchants;")
    assert r_missing[0]["count"] == 0

    # 2. Unassigned role -> fails closed
    r_unassigned = db.execute_with_rls_context(claims={"app_metadata": {"role": "unassigned"}}, query_sql="SELECT count(*) FROM public.merchants;")
    assert r_unassigned[0]["count"] == 0

    # 3. Invalid/attacker role -> fails closed
    r_attacker = db.execute_with_rls_context(claims={"app_metadata": {"role": "attacker"}}, query_sql="SELECT count(*) FROM public.merchants;")
    assert r_attacker[0]["count"] == 0

    # 4. Valid roles evaluate properly
    for valid_role in ["customer", "fraud_investigator", "admin"]:
        r_valid = db.execute_with_rls_context(claims={"app_metadata": {"role": valid_role}}, query_sql="SELECT count(*) FROM public.merchants;")
        assert "count" in r_valid[0]

# ------------------------------------------------------------------------------
# Test U: Customer Cannot Manipulate Claims or Request Another Card
# ------------------------------------------------------------------------------
def test_u_customer_cannot_manipulate_claims_or_card_id():
    # 1. Customer Charlie has CARD_007 bound in verified credentials
    charlie_login = client.post("/api/v1/auth/login", json={
        "email": "customer.charlie@bank.com",
        "password": "SentinelPass2026!"
    })
    assert charlie_login.status_code == 200
    token = charlie_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Charlie attempts to request Elena's CARD_012 via query parameter -> 403 Forbidden
    elena_txns = client.get("/api/v1/customer/transactions?card_id=CARD_012", headers=headers)
    assert elena_txns.status_code == 403
    assert "Forbidden" in elena_txns.json()["detail"]

    # 3. Malicious user attempts to pass user_metadata card_id override -> ignored
    tampered_token = make_test_token(
        sub="usr_tampered",
        email="customer.card007@sentinel.ai",
        app_meta_role="customer",
        card_id="CARD_007"
    )
    tampered_headers = {"Authorization": f"Bearer {tampered_token}"}
    override_attempt = client.get("/api/v1/customer/transactions?card_id=CARD_999", headers=tampered_headers)
    assert override_attempt.status_code == 403
    assert "Forbidden" in override_attempt.json()["detail"]


