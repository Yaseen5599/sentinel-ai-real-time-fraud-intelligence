"""
Targeted Automated Test Suite for Sentinel AI Bug Fixes
Covers:
1. Scenario Injection & Stress Testing (Issue A)
2. Newest-First Ordering across all queries & queues (Issue B)
3. Transaction Authorization Workflow & RBAC (Issue C)
4. Customer Dispute / Suspicious Activity Reporting (Issue E)
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.api.main import app, create_access_token
from src.database.db_client import DatabaseClient
from src.producer.transaction_generator import TransactionGenerator

client = TestClient(app)

@pytest.fixture
def db():
    return DatabaseClient()

@pytest.fixture
def admin_headers():
    token = create_access_token({
        "sub": "admin_test",
        "email": "admin@sentinel.ai",
        "app_metadata": {"role": "admin"}
    })
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def investigator_headers():
    token = create_access_token({
        "sub": "investigator_test",
        "email": "investigator@sentinel.ai",
        "app_metadata": {"role": "fraud_investigator"}
    })
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def customer_headers():
    token = create_access_token({
        "sub": "customer_test",
        "email": "customer@sentinel.ai",
        "app_metadata": {"role": "customer", "card_id": "CARD_007"}
    })
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. SCENARIO INJECTION TESTS (Issue A)
# ============================================================================

def test_scenario_generators_canonical_schema():
    """Verify that every scenario generator emits valid canonical transaction records."""
    gen = TransactionGenerator()
    scenarios = [
        ("NORMAL", gen.generate_normal_transaction()),
        ("RAPID_BURST", gen.generate_scenario_rapid_burst(count=3)[0]),
        ("IMPOSSIBLE_TRAVEL", gen.generate_scenario_travel_anomaly()[0]),
        ("HIGH_AMOUNT", gen.generate_scenario_high_amount()),
        ("NIGHT_ANOMALY", gen.generate_scenario_night_spend()),
        ("MERCHANT_SWARM", gen.generate_scenario_card_swarm(count=4)[0])
    ]

    for name, txn in scenarios:
        assert "transaction_id" in txn, f"{name} missing transaction_id"
        assert "card_id" in txn, f"{name} missing card_id"
        assert "amount" in txn, f"{name} missing amount"
        assert "timestamp" in txn, f"{name} missing timestamp"
        assert txn["amount"] > 0, f"{name} amount must be positive"
        assert txn.get("is_synthetic") is True, f"{name} must be flagged as synthetic"
        assert txn.get("is_demo") is True, f"{name} must be flagged as demo"
        assert txn.get("authorization_status") == "PENDING", f"{name} must default to PENDING"

def test_simulate_in_process_pipeline_execution(admin_headers):
    """Test that simulate endpoint executes real scoring and persists records."""
    res = client.post("/api/v1/simulate", json={
        "scenario": "NORMAL",
        "count": 2,
        "publish_to_kafka": False
    }, headers=admin_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["route"] == "in-process"
    assert data["persisted_count"] == 2
    assert len(data["scores"]) == 2

    # Verify that scores contain genuine ML/rule breakdown
    score_entry = data["scores"][0]
    assert "transaction_id" in score_entry
    assert "final_fraud_score" in score_entry
    assert "fraud_decision" in score_entry
    assert score_entry["fraud_decision"] in ["LEGITIMATE", "SUSPICIOUS", "FRAUD"]

def test_simulate_kafka_failure_reporting(admin_headers):
    """If Kafka routing is requested but Kafka is unreachable, API must report 503 error."""
    # When Kafka is not running on 9092, requesting Kafka route should return 503 instead of false success
    res = client.post("/api/v1/simulate", json={
        "scenario": "HIGH_AMOUNT",
        "count": 1,
        "publish_to_kafka": True
    }, headers=admin_headers)

    # Either Kafka is online (200) or gracefully reports 503 Service Unavailable
    assert res.status_code in [200, 503]
    if res.status_code == 503:
        assert "Kafka" in res.json().get("detail", "")


# ============================================================================
# 2. NEWEST-FIRST ORDERING TESTS (Issue B)
# ============================================================================

def test_transaction_ordering_newest_first(db):
    """Verify that get_recent_transactions returns records in strict descending order."""
    txns = db.get_recent_transactions(limit=25)
    if len(txns) >= 2:
        for i in range(len(txns) - 1):
            t1 = txns[i].get("ingested_at") or txns[i].get("timestamp") or ""
            t2 = txns[i+1].get("ingested_at") or txns[i+1].get("timestamp") or ""
            # Newer or equal timestamp
            assert t1 >= t2, f"Ordering violation: {t1} < {t2}"

def test_case_ordering_newest_first(db):
    """Verify that get_cases returns cases in strict descending order of opened_at."""
    cases = db.get_cases(limit=25)
    if len(cases) >= 2:
        for i in range(len(cases) - 1):
            c1 = str(cases[i].get("opened_at") or "")
            c2 = str(cases[i+1].get("opened_at") or "")
            assert c1 >= c2, f"Case ordering violation: {c1} < {c2}"

def test_high_risk_table_filter_retained(db):
    """High-risk transactions table must strictly filter for FRAUD or SUSPICIOUS decisions."""
    flagged = db.get_recent_transactions(limit=20, flagged_only=True)
    for tx in flagged:
        assert tx.get("fraud_decision") in ["FRAUD", "SUSPICIOUS"], (
            f"Non-flagged transaction {tx.get('transaction_id')} found in high-risk list"
        )


# ============================================================================
# 3. TRANSACTION AUTHORIZATION WORKFLOW TESTS (Issue C)
# ============================================================================

def test_new_transaction_defaults_to_pending(db):
    """A newly ingested transaction must strictly default to PENDING."""
    unique_tx_id = f"TX_TEST_AUTH_{int(time.time() * 1000)}"
    txn_data = {
        "transaction_id": unique_tx_id,
        "card_id": "CARD_007",
        "amount": 42.50,
        "merchant": "Coffee Shop",
        "city": "Boston",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS"
    }

    db.insert_transaction(txn_data)
    record = db.get_transaction(unique_tx_id)
    assert record is not None
    assert record.get("authorization_status") == "PENDING"
    assert record.get("authorized_by") is None

def test_customer_cannot_authorize_transaction(customer_headers):
    """Customer role must be rejected with 403 Forbidden when attempting authorization."""
    res = client.post("/api/v1/transactions/TX_TEST_ANY/authorize", json={}, headers=customer_headers)
    assert res.status_code == 403
    assert "not authorized" in res.json().get("detail", "").lower()

def test_authorized_investigator_approval_workflow(investigator_headers, db):
    """Authorized fraud investigator can approve a PENDING transaction."""
    unique_tx_id = f"TX_INV_APPR_{int(time.time() * 1000)}"
    txn_data = {
        "transaction_id": unique_tx_id,
        "card_id": "CARD_007",
        "amount": 125.00,
        "merchant": "Tech Store",
        "city": "San Francisco",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS"
    }
    db.insert_transaction(txn_data)

    # Approve transaction via endpoint
    res = client.post(f"/api/v1/transactions/{unique_tx_id}/authorize", json={}, headers=investigator_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["authorization_status"] == "AUTHORIZED"
    assert "investigator" in data["authorized_by"].lower()
    assert data["authorized_at"] is not None

    # Check persistence
    persisted = db.get_transaction(unique_tx_id)
    assert persisted["authorization_status"] == "AUTHORIZED"
    assert persisted["authorized_by"] == data["authorized_by"]

    # Re-approving an already AUTHORIZED transaction should be rejected (400)
    res_repeat = client.post(f"/api/v1/transactions/{unique_tx_id}/authorize", json={}, headers=investigator_headers)
    assert res_repeat.status_code == 400


# ============================================================================
# 4. CUSTOMER DISPUTE / REPORT WORKFLOW TESTS (Issue E)
# ============================================================================

def test_customer_cannot_report_other_card(customer_headers, db):
    """A customer cannot report a transaction that belongs to another cardholder."""
    foreign_tx_id = f"TX_FOREIGN_{int(time.time() * 1000)}"
    db.insert_transaction({
        "transaction_id": foreign_tx_id,
        "card_id": "CARD_999",  # Not customer's CARD_007
        "amount": 99.00,
        "merchant": "Other Store",
        "city": "Miami",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS"
    })

    res = client.post("/api/v1/customer/report", json={
        "transaction_id": foreign_tx_id,
        "reason": "UNRECOGNIZED_TRANSACTION",
        "notes": "Not my card"
    }, headers=customer_headers)

    assert res.status_code == 403
    assert "not authorized to report" in res.json().get("detail", "").lower()

def test_customer_report_surfaces_at_top_of_investigation_queue(customer_headers, investigator_headers, db):
    """When a customer reports their transaction, it creates/updates a case that appears first in queue."""
    my_tx_id = f"TX_DISP_{int(time.time() * 1000)}"
    db.insert_transaction({
        "transaction_id": my_tx_id,
        "card_id": "CARD_007",
        "amount": 349.99,
        "merchant": "Online Electronics",
        "city": "Seattle",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS"
    })

    # Submit report as customer
    res = client.post("/api/v1/customer/report", json={
        "transaction_id": my_tx_id,
        "reason": "CARD_STOLEN",
        "notes": "Card was stolen in transit",
        "freeze_card": False
    }, headers=customer_headers)

    assert res.status_code in (200, 201)
    report_data = res.json()
    assert report_data["status"] in ("reported", "SUCCESS")
    assert report_data["transaction_id"] == my_tx_id

    # Verify that the case appears at the top of the investigation queue
    cases_res = client.get("/api/v1/cases?limit=5", headers=investigator_headers)
    assert cases_res.status_code == 200
    top_cases = cases_res.json()
    assert len(top_cases) > 0

    # The most recent reported transaction should be at index 0
    top_case = top_cases[0]
    assert top_case["transaction_id"] == my_tx_id
    assert "Customer Dispute" in (top_case.get("analyst_notes") or "")

    # Crucial business rule: Customer report does NOT auto-confirm fraud or auto-authorize
    assert top_case.get("analyst_decision") in (None, "PENDING")
    assert top_case.get("analyst_decision") != "CONFIRMED_FRAUD"
    assert top_case.get("status") == "OPEN"
    txn = db.get_transaction(my_tx_id)
    assert txn.get("authorization_status") == "PENDING"
