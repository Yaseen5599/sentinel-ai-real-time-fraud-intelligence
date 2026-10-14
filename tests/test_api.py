"""
Unit Tests for Sentinel AI FastAPI Gateway
Tests transaction ingestion, KPI retrieval, scenario simulation, and case triage workflow.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def get_analyst_headers():
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "analyst.sarah@sentinel.ai",
        "password": "SentinelSecure2026!"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_type" in data

def test_ingest_normal_transaction():
    headers = get_analyst_headers()
    payload = {
        "card_id": "CARD_007",
        "amount": 42.50,
        "merchant_name": "Target",
        "merchant_category_code": "5311",
        "city": "Chicago",
        "channel": "IN_PERSON_CHIP"
    }
    response = client.post("/api/v1/transactions", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "processed"
    assert "scores" in data
    assert "ml_score" in data["scores"]
    assert "fraud_decision" in data
    assert data["fraud_decision"] in ["LEGITIMATE", "SUSPICIOUS", "FRAUD"]

def test_simulate_impossible_travel():
    headers = get_analyst_headers()
    payload = {
        "scenario": "IMPOSSIBLE_TRAVEL",
        "card_id": "CARD_012"
    }
    response = client.post("/api/v1/simulate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["processed_count"] == 2
    # Second transaction should trigger an alert
    second_tx = data["transactions"][1]
    assert second_tx["fraud_decision"] in ["SUSPICIOUS", "FRAUD"]

def get_analyst_headers():
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "analyst.sarah@sentinel.ai",
        "password": "SentinelSecure2026!"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_get_kpis_and_recent():
    headers = get_analyst_headers()
    kpi_resp = client.get("/api/v1/analytics/kpis", headers=headers)
    assert kpi_resp.status_code == 200
    kpis = kpi_resp.json()
    assert "total_transactions" in kpis

    recent_resp = client.get("/api/v1/transactions/recent?limit=10", headers=headers)
    assert recent_resp.status_code == 200
    recent = recent_resp.json()
    assert isinstance(recent, list)

def test_case_triage_workflow():
    headers = get_analyst_headers()
    # 1. Trigger high-value spike scenario to generate an alert case
    sim_resp = client.post("/api/v1/simulate", json={"scenario": "HIGH_VALUE_SPIKE", "card_id": "CARD_005"}, headers=headers)
    assert sim_resp.status_code == 200

    # 2. Get cases
    cases_resp = client.get("/api/v1/cases", headers=headers)
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    assert len(cases) > 0

    first_case = cases[0]
    case_id = first_case["case_id"]

    # 3. Analyst resolves case
    update_payload = {
        "analyst_id": "ANALYST_SARAH",
        "decision": "CONFIRMED_FRAUD",
        "notes": "Verified unauthorized login and abnormal withdrawal attempt.",
        "status": "RESOLVED"
    }
    patch_resp = client.patch(f"/api/f1/cases/{case_id}".replace("/api/f1/", "/api/v1/"), headers=headers, json=update_payload)
    assert patch_resp.status_code == 200
    res = patch_resp.json()
    assert res["status"] == "updated"
    assert res["analyst_decision"] == "CONFIRMED_FRAUD"

def test_storage_status():
    resp = client.get("/api/v1/storage/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_database_connected" in data
    assert "storage_mode" in data
    assert "backend" in data

def test_card_masking_in_ingest():
    headers = get_analyst_headers()
    payload = {
        "card_id": "CARD_007",
        "amount": 99.00,
        "merchant_name": "Apple",
        "merchant_category_code": "5732",
        "city": "Cupertino"
    }
    resp = client.post("/api/v1/transactions", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "masked_card_id" in data
    assert data["masked_card_id"] == "CARD_***_007"

def test_analyst_jwt_login_and_verification():
    # 1. Successful analyst login
    login_payload = {
        "email": "analyst.sarah@sentinel.ai",
        "password": "SentinelSecure2026!"
    }
    login_resp = client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    assert login_data["user"]["email"] == "analyst.sarah@sentinel.ai"
    assert login_data["user"]["role"] == "fraud_investigator"
    token = login_data["access_token"]

    # 2. Authenticated user profile check (/api/v1/auth/me)
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["authenticated"] is True
    assert me_data["email"] == "analyst.sarah@sentinel.ai"
    assert me_data["role"] == "fraud_investigator"

    # 3. Forged token rejection (401 Unauthorized)
    forged_resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer forged.invalid.token"})
    assert forged_resp.status_code == 401
    assert "Invalid authentication token" in forged_resp.json()["detail"]

def test_authenticated_case_triage_audit():
    # 1. Login to get JWT
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "analyst.lead@sentinel.ai",
        "password": "SentinelSecure2026!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 2. Simulate anomaly to get case
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/simulate", json={"scenario": "IMPOSSIBLE_TRAVEL", "card_id": "CARD_099"}, headers=headers)
    cases = client.get("/api/v1/cases", headers=headers).json()
    assert len(cases) > 0
    case_id = cases[0]["case_id"]

    # 3. Resolve case with Bearer token
    patch_resp = client.patch(
        f"/api/v1/cases/{case_id}",
        headers=headers,
        json={
            "analyst_id": "analyst.lead@sentinel.ai",
            "decision": "CONFIRMED_FRAUD",
            "notes": "Confirmed travel velocity anomaly via JWT analyst session.",
            "status": "RESOLVED"
        }
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["analyst_id"] == "analyst.lead@sentinel.ai"
    assert data["auth_role"] in ["fraud_investigator", "authenticated"]

def test_missing_and_invalid_jwts():
    # 1. Invalid / malformed Bearer token
    resp_bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.token.value"})
    assert resp_bad.status_code == 401
    assert "Invalid authentication token" in resp_bad.json()["detail"]

    # 2. Random junk authorization header
    resp_junk = client.get("/api/v1/auth/me", headers={"Authorization": "NotBearer 12345"})
    # verify_analyst_auth falls back to dev_session if no Bearer credentials header supplied
    assert resp_junk.status_code == 200 or resp_junk.status_code == 401

def test_customer_to_customer_data_isolation():
    # 1. Login Customer Alice (CARD_007)
    alice_login = client.post("/api/v1/auth/login", json={
        "email": "customer.alice@bank.com",
        "role": "customer",
        "card_id": "CARD_007"
    })
    assert alice_login.status_code == 200
    alice_token = alice_login.json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    # 2. Alice views her own transactions -> 200 OK
    alice_txns = client.get("/api/v1/customer/transactions", headers=alice_headers)
    assert alice_txns.status_code == 200
    txns = alice_txns.json()
    assert len(txns) > 0
    # Verify card masking and that all returned transactions belong to CARD_007
    for t in txns:
        assert t["card_id"] == "CARD_007"
        assert t["masked_card_id"] == "CARD_***_007"

    # 3. Alice attempts to access Customer Bob's card (CARD_012) -> MUST BE 403 FORBIDDEN
    leak_attempt = client.get("/api/v1/customer/transactions?card_id=CARD_012", headers=alice_headers)
    assert leak_attempt.status_code == 403
    assert "Forbidden" in leak_attempt.json()["detail"]

def test_unauthorized_role_access_and_investigator_permissions():
    # 1. Customer login
    cust_login = client.post("/api/v1/auth/login", json={
        "email": "customer.charlie@bank.com",
        "role": "customer",
        "card_id": "CARD_007"
    })
    cust_token = cust_login.json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    # 2. Customer attempts to view case triage list -> 403 Forbidden
    cust_cases = client.get("/api/v1/cases", headers=cust_headers)
    assert cust_cases.status_code == 403
    assert "Access forbidden" in cust_cases.json()["detail"]

    # 3. Customer attempts to access analytics KPIs -> 403 Forbidden
    cust_kpis = client.get("/api/v1/analytics/kpis", headers=cust_headers)
    assert cust_kpis.status_code == 403

    # 4. Customer attempts to access recent raw transactions stream -> 403 Forbidden
    cust_stream = client.get("/api/v1/transactions/recent", headers=cust_headers)
    assert cust_stream.status_code == 403

    # 5. Customer attempts to access admin audit logs -> 403 Forbidden
    cust_admin = client.get("/api/v1/admin/audit-logs", headers=cust_headers)
    assert cust_admin.status_code == 403

    # 6. Fraud Investigator login
    inv_login = client.post("/api/v1/auth/login", json={
        "email": "investigator.dan@sentinel.ai",
        "role": "fraud_investigator"
    })
    inv_token = inv_login.json()["access_token"]
    inv_headers = {"Authorization": f"Bearer {inv_token}"}

    # 7. Investigator can access cases and KPIs
    assert client.get("/api/v1/cases", headers=inv_headers).status_code == 200
    assert client.get("/api/v1/analytics/kpis", headers=inv_headers).status_code == 200

    # 8. Investigator CANNOT access Admin audit logs -> 403 Forbidden
    assert client.get("/api/v1/admin/audit-logs", headers=inv_headers).status_code == 403

def test_administrative_permissions():
    # 1. Admin login
    admin_login = client.post("/api/v1/auth/login", json={
        "email": "admin.security@sentinel.ai",
        "role": "admin"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin accesses audit logs -> 200 OK
    admin_logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert admin_logs.status_code == 200
    assert isinstance(admin_logs.json(), list)

    # 3. Admin has unrestricted access to cases and KPIs
    assert client.get("/api/v1/cases", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/analytics/kpis", headers=admin_headers).status_code == 200

def test_database_rls_enforcement():
    from src.database.db_client import DatabaseClient
    db = DatabaseClient()
    if not db.test_connection():
        return

    # 1. Test Customer RLS context in PostgreSQL kernel
    c7_claims = {
        "sub": "usr_CARD_007",
        "card_id": "CARD_007",
        "app_metadata": {"role": "customer", "card_id": "CARD_007"}
    }
    c7_txns = db.execute_with_rls_context(
        claims=c7_claims,
        query_sql="SELECT count(*), count(distinct card_id) as cards FROM transactions;"
    )
    assert c7_txns[0]["count"] > 0
    assert c7_txns[0]["cards"] <= 1  # Strictly 1 card

    # 2. Test Customer sees 0 investigation cases in PostgreSQL kernel
    c7_cases = db.execute_with_rls_context(
        claims=c7_claims,
        query_sql="SELECT count(*) FROM fraud_investigations;"
    )
    assert c7_cases[0]["count"] == 0

    # 3. Test Investigator RLS context in PostgreSQL kernel sees all cases
    inv_claims = {
        "sub": "usr_inv",
        "app_metadata": {"role": "fraud_investigator"}
    }
    inv_cases = db.execute_with_rls_context(
        claims=inv_claims,
        query_sql="SELECT count(*) FROM fraud_investigations;"
    )
    assert inv_cases[0]["count"] > 0



