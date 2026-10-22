"""
Unit & Integration Tests for Transaction Risk Analysis
Tests the 10,000-dataset generation, canonical scoring pipeline,
FastAPI endpoints, RBAC authorization, and arithmetic verification.
"""

import math
from fastapi.testclient import TestClient
from src.api.main import app
from scripts.generate_real_data_csvs import validate_datasets, CARDHOLDERS_CSV, TRANSACTIONS_CSV
from src.api.transaction_risk_analysis import TransactionRiskAnalysisService

client = TestClient(app)

def get_investigator_headers():
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "analyst.sarah@sentinel.ai",
        "password": "SentinelSecure2026!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def get_customer_headers():
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "customer.card007@sentinel.ai",
        "password": "SentinelSecure2026!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_dataset_generation_and_validation():
    """Validates the generated CSV files conform to all requirements."""
    report = validate_datasets(CARDHOLDERS_CSV, TRANSACTIONS_CSV)
    assert report["status"] == "PASSED"
    assert report["transactions_count"] == 10000
    assert report["cardholders_count"] == 60
    assert report["error_count"] == 0

def test_risk_analysis_endpoint_success():
    """Tests successful analysis of a valid transaction ID."""
    headers = get_investigator_headers()
    response = client.post(
        "/api/v1/transaction-risk-analysis",
        json={"transaction_id": "T00001"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()

    assert data["found"] is True
    assert data["transaction_id"] == "T00001"
    assert "amount" in data
    assert "merchant" in data
    assert "location" in data
    assert "card_id_masked" in data
    assert data["card_id_masked"].startswith("CARD_***")
    assert data["is_synthetic"] is True

    # Check score structure
    scores = data["scores"]
    assert "ml_score" in scores
    assert "behavior_score" in scores
    assert "rule_score" in scores
    assert "final_risk_score" in scores
    assert scores["classification"] in ["LEGITIMATE", "SUSPICIOUS", "HIGH_RISK"]

    # Verify arithmetic formula
    w_ml = scores["weights"]["ml_weight"]
    w_beh = scores["weights"]["behavior_weight"]
    w_rule = scores["weights"]["rule_weight"]
    ml_s = scores["ml_score"]
    beh_s = scores["behavior_score"]
    rule_s = scores["rule_score"]
    expected_score = round(min(1.0, max(0.0, (w_ml * ml_s) + (w_beh * beh_s) + (w_rule * rule_s))), 4)
    assert math.isclose(scores["final_risk_score"], expected_score, abs_tol=1e-3)

    # Check explanations
    explanations = data["explanations"]
    assert "plain_english_audit" in explanations
    assert len(explanations["plain_english_audit"]) > 20
    assert "ml" in explanations
    assert "behavior" in explanations
    assert "rules" in explanations
    assert "hybrid" in explanations

def test_risk_analysis_endpoint_unknown_id():
    """Tests 404 response for unknown transaction ID."""
    headers = get_investigator_headers()
    response = client.post(
        "/api/v1/transaction-risk-analysis",
        json={"transaction_id": "T99999"},
        headers=headers
    )
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_risk_analysis_endpoint_invalid_format():
    """Tests rejection of illegal path traversal / SQL injection characters."""
    headers = get_investigator_headers()
    response = client.post(
        "/api/v1/transaction-risk-analysis",
        json={"transaction_id": "../../../etc/passwd"},
        headers=headers
    )
    assert response.status_code == 400

def test_risk_analysis_endpoint_unauthorized():
    """Tests rejection of unauthenticated requests."""
    response = client.post(
        "/api/v1/transaction-risk-analysis",
        json={"transaction_id": "T00001"}
    )
    assert response.status_code == 401

def test_risk_analysis_endpoint_customer_forbidden():
    """Tests that customers cannot access investigator risk analysis."""
    headers = get_customer_headers()
    response = client.post(
        "/api/v1/transaction-risk-analysis",
        json={"transaction_id": "T00001"},
        headers=headers
    )
    assert response.status_code == 403

def test_sample_ids_endpoint():
    """Tests retrieval of curated sample transaction IDs."""
    headers = get_investigator_headers()
    response = client.get("/api/v1/transaction-risk-analysis/sample-ids", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert len(data["samples"]) >= 4
    sample_ids = [s["id"] for s in data["samples"]]
    assert "T00001" in sample_ids
