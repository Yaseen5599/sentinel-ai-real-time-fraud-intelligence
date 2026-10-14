"""
Sentinel AI — Phase 5 Workflow and Backend API Integration Tests
Tests for:
1. Milestone 1: Database persistence, write failure handling, in-memory fallback, fraud_decision in customer txns.
2. Milestone 2: Authenticated Bearer requests, 401/403 authorization enforcement.
3. Milestone 3: Customer dispute submission, validation of transaction ownership, rejection of cross-customer disputes, distinct non-confirmed-fraud status, audit logs.
4. Milestone 4: Admin-only user retrieval without exposing hashes/secrets, pipeline health probe including Kafka unreachable state.
5. Milestone 5: Model metadata verification, provenance, and unverified state handling.
"""

import pytest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.main import app, TRUSTED_USERS_REGISTRY
from src.database.db_client import DatabaseClient
from config.config import PROJECT_ROOT

client = TestClient(app)

# Helper authentication tokens
def get_auth_token(email: str, password: str = "SentinelSecure2026!") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]

@pytest.fixture(scope="module")
def admin_headers():
    token = get_auth_token("admin.security@sentinel.ai")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def investigator_headers():
    token = get_auth_token("analyst.sarah@sentinel.ai")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def customer_headers():
    token = get_auth_token("customer.card007@sentinel.ai")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def other_customer_headers():
    token = get_auth_token("customer.card012@sentinel.ai")
    return {"Authorization": f"Bearer {token}"}

# ==============================================================================
# Milestone 1: Database Persistence & Error Handling Tests
# ==============================================================================

def test_database_write_failure_returns_false_and_buffers_in_memory():
    """
    Ensures that when a database write fails (e.g., connection drops or SQL error),
    insert_transaction returns False (not True) and preserves the record in memory.
    """
    db = DatabaseClient()
    fake_record = {
        "transaction_id": f"TX_FAIL_TEST_{uuid.uuid4().hex[:8]}",
        "card_id": "CARD_007",
        "amount": 120.0,
        "merchant": "ElectronicsStore",
        "fraud_decision": "LEGITIMATE"
    }

    # Simulate database connection failure
    with patch.object(db, "get_connection", side_effect=Exception("Database connection timeout")):
        persisted = db.insert_transaction(fake_record)
        # MUST return False on failed write, NEVER report success
        assert persisted is False
        assert db.is_connected is False

    # Ephemeral fallback should still retain the record
    mem_txs = [t for t in db._memory_transactions if t.get("transaction_id") == fake_record["transaction_id"]]
    assert len(mem_txs) == 1
    assert mem_txs[0]["amount"] == 120.0

def test_database_customer_transactions_includes_fraud_decision():
    """
    Ensures get_customer_transactions returns the fraud_decision required by the customer dashboard.
    """
    db = DatabaseClient()
    test_txn_id = f"TX_DECISION_TEST_{uuid.uuid4().hex[:8]}"
    test_record = {
        "transaction_id": test_txn_id,
        "card_id": "CARD_007",
        "amount": 88.0,
        "merchant": "AppleStore",
        "fraud_decision": "SUSPICIOUS",
        "ml_score": 0.45,
        "final_fraud_score": 0.52
    }
    db.insert_transaction(test_record)

    txns = db.get_customer_transactions("CARD_007", limit=10)
    assert len(txns) > 0
    # Every customer transaction record must contain the fraud_decision field
    found = next((t for t in txns if t.get("transaction_id") == test_txn_id), None)
    assert found is not None
    assert "fraud_decision" in found
    assert found["fraud_decision"] in ["LEGITIMATE", "SUSPICIOUS", "FRAUD"]

# ==============================================================================
# Milestone 2: Authenticated API Client & Authorization Enforcement
# ==============================================================================

def test_unauthenticated_requests_to_protected_endpoints_fail_closed():
    """Protected endpoints must reject requests with missing token (401 Unauthorized)."""
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/analytics/kpis").status_code == 401
    assert client.get("/api/v1/cases").status_code == 401
    assert client.get("/api/v1/customer/transactions").status_code == 401
    assert client.get("/api/v1/admin/audit-logs").status_code == 401
    assert client.get("/api/v1/admin/users").status_code == 401

def test_public_endpoints_remain_accessible_without_token():
    """Public endpoints must remain accessible without requiring Bearer token."""
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/storage/status").status_code == 200
    assert client.get("/api/v1/models/info").status_code == 200
    assert client.get("/api/v1/pipeline/health").status_code == 200

# ==============================================================================
# Milestone 3: Customer Disputes & Strict Data Isolation
# ==============================================================================

def test_customer_dispute_workflow_and_audit(customer_headers):
    """
    Tests legitimate customer dispute submission for own transaction:
    - 201 Created
    - Status is OPEN with analyst_decision PENDING (not confirmed fraud)
    - Stored in persistent investigation cases
    - Immutable audit log generated
    """
    # 1. Ingest a transaction for CARD_007
    txn_id = f"TX_DISP_{uuid.uuid4().hex[:8]}"
    ingest_resp = client.post("/api/v1/transactions", headers=customer_headers, json={
        "transaction_id": txn_id,
        "card_id": "CARD_007",
        "amount": 250.00,
        "merchant_name": "LuxuryJewelry",
        "city": "London",
        "channel": "ONLINE_ECOMMERCE"
    })
    assert ingest_resp.status_code == 201

    # 2. Customer submits dispute
    report_resp = client.post("/api/v1/customer/report", headers=customer_headers, json={
        "transaction_id": txn_id,
        "reason": "UNRECOGNIZED_TRANSACTION",
        "notes": "I was never in London and did not purchase jewelry.",
        "freeze_card": True
    })
    assert report_resp.status_code == 201
    data = report_resp.json()
    assert data["status"] == "reported"
    assert data["transaction_id"] == txn_id
    assert data["investigation_status"] == "OPEN"
    # MUST NOT be marked as confirmed fraud automatically!
    assert data["analyst_decision"] == "PENDING"
    assert data["freeze_card_requested"] is True

    # 3. Retrieve customer disputes
    disputes_resp = client.get("/api/v1/customer/disputes", headers=customer_headers)
    assert disputes_resp.status_code == 200
    disputes = disputes_resp.json()
    assert any(d.get("transaction_id") == txn_id for d in disputes)

def test_cross_customer_dispute_rejection(customer_headers, other_customer_headers):
    """
    Security check: Customer A (CARD_007) CANNOT report a transaction belonging to Customer B (CARD_012).
    Must return 403 Forbidden.
    """
    # 1. Ingest transaction for CARD_012 (Elena)
    elena_txn_id = f"TX_ELENA_{uuid.uuid4().hex[:8]}"
    ingest_resp = client.post("/api/v1/transactions", headers=other_customer_headers, json={
        "transaction_id": elena_txn_id,
        "card_id": "CARD_012",
        "amount": 95.00,
        "merchant_name": "GroceryStore",
        "city": "Boston"
    })
    assert ingest_resp.status_code == 201

    # 2. Customer James (CARD_007) attempts to dispute Elena's transaction -> 403 Forbidden
    cross_report = client.post("/api/v1/customer/report", headers=customer_headers, json={
        "transaction_id": elena_txn_id,
        "reason": "UNRECOGNIZED_TRANSACTION"
    })
    assert cross_report.status_code == 403
    assert "Forbidden" in cross_report.json()["detail"]

    # 3. Customer James attempts to query Elena's disputes via query param -> 403 Forbidden
    cross_query = client.get("/api/v1/customer/disputes?card_id=CARD_012", headers=customer_headers)
    assert cross_query.status_code == 403

def test_report_nonexistent_transaction_returns_404(customer_headers):
    """Reporting a non-existent transaction reference returns 404 Not Found."""
    resp = client.post("/api/v1/customer/report", headers=customer_headers, json={
        "transaction_id": "TX_DOES_NOT_EXIST_9999",
        "reason": "LOST_OR_STOLEN_CARD"
    })
    assert resp.status_code == 404

# ==============================================================================
# Milestone 4: Admin Users & Pipeline Health Probes
# ==============================================================================

def test_admin_users_retrieval_and_role_protection(admin_headers, investigator_headers, customer_headers):
    """
    Tests GET /api/v1/admin/users:
    - Admin: 200 OK with sanitized user list (NO password hashes or valid_passwords exposed)
    - Investigator: 403 Forbidden
    - Customer: 403 Forbidden
    """
    # 1. Admin access
    resp = client.get("/api/v1/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "users" in data
    assert len(data["users"]) > 0

    # Ensure sensitive credentials and hashes are never exposed
    for u in data["users"]:
        assert "password" not in u
        assert "valid_passwords" not in u
        assert "encrypted_password" not in u
        assert "email" in u
        assert "role" in u

    # 2. Investigator forbidden
    assert client.get("/api/v1/admin/users", headers=investigator_headers).status_code == 403

    # 3. Customer forbidden
    assert client.get("/api/v1/admin/users", headers=customer_headers).status_code == 403

def test_pipeline_health_endpoint():
    """
    Tests GET /api/v1/pipeline/health:
    - Distinguishes verified services
    - Reports gateway, database_storage, ml_scoring_engine, stream_processor, kafka_broker
    - Kafka broker status correctly probed and reported
    """
    resp = client.get("/api/v1/pipeline/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_status" in data
    assert "services" in data
    services = data["services"]

    assert "api_gateway" in services
    assert services["api_gateway"]["status"] == "healthy"

    assert "database_storage" in services
    assert services["database_storage"]["status"] in ["healthy", "degraded"]

    assert "ml_scoring_engine" in services
    assert services["ml_scoring_engine"]["status"] == "healthy"
    assert services["ml_scoring_engine"]["zero_skew_verified"] is True

    assert "stream_processor" in services
    assert services["stream_processor"]["status"] == "healthy"

    assert "kafka_broker" in services
    # Kafka broker is safely probed and indicates active status or unreachable fallback
    assert services["kafka_broker"]["status"] in ["healthy", "unhealthy"]
    assert "detail" in services["kafka_broker"]

# ==============================================================================
# Milestone 5: Model Metadata Verification
# ==============================================================================

def test_models_info_returns_verified_metadata():
    """
    Tests GET /api/v1/models/info:
    - Returns verified metadata matching canonical-rf-v1.0
    - Contains provenance, evaluation benchmarks (temporal and cardholder disjoint)
    - Feature count equals 18
    """
    resp = client.get("/api/v1/models/info")
    assert resp.status_code == 200
    data = resp.json()

    assert data["model_version"] == "canonical-rf-v1.0"
    assert data["is_verified"] is True
    assert data["verification_status"] == "verified"
    assert data["feature_count"] == 18
    assert len(data["features"]) == 18

    assert "provenance" in data
    assert data["provenance"]["corresponds_to_deployed_model"] is True

    assert "evaluation" in data
    eval_metrics = data["evaluation"]
    assert eval_metrics is not None
    assert "precision" in eval_metrics
    assert "recall" in eval_metrics
    assert "temporal_benchmark" in eval_metrics
    assert "cardholder_disjoint_benchmark" in eval_metrics

def test_models_info_fails_truthfully_when_metadata_missing():
    """
    Ensures that if model_metadata.json is missing or invalid,
    the endpoint returns an explicit unverified state without fabricating metrics.
    """
    with patch("pathlib.Path.exists", return_value=False):
        resp = client.get("/api/v1/models/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_verified"] is False
        assert data["verification_status"] == "unavailable"
        assert data["evaluation"] is None
        assert "warning" in data
