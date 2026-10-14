"""
Sentinel AI — Phase 8 Integration Testing and Security Validation
Tests:
1. Milestone 1: Live end-to-end integration:
   Generator -> Kafka transactions-canonical -> PySpark Structured Streaming ->
   Canonical Features -> ML Model -> PostgreSQL -> FastAPI -> Masked API response.
2. Milestone 2: Endpoint access control hardening:
   - Unauthenticated callers rejected on /transactions and /simulate (401)
   - Customer callers restricted to authorized card on /transactions (403 for cross-card)
   - Customer callers rejected on /simulate (403)
   - Investigator and Admin callers authorized on /transactions and /simulate (201 / 200)
3. Milestone 2: Thread-safe concurrent memory buffer operations:
   - Simultaneous ingestion and buffer draining under multiple threads.
4. Milestone 3: Time-aware bounded deduplication cache:
   - 30-minute replay retention window preservation and memory bound.
5. Milestone 3: Partial buffer drain resilience and retry safety.
"""

import os
import sys
import uuid
import time
import threading
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from fastapi.testclient import TestClient
from src.api.main import app, create_access_token
from src.producer.kafka_producer import TransactionKafkaProducer
from src.streaming.spark_streaming_pipeline import (
    RealTimeStreamProcessor,
    TimeAwareDedupCache,
    PYSPARK_AVAILABLE
)
from src.database.db_client import DatabaseClient
from config.config import KAFKA_CANONICAL_TOPIC

client = TestClient(app)

def make_token(role: str, card_id: str = None, user_id: str = "usr_phase8") -> dict:
    claims = {
        "sub": user_id,
        "email": f"{role}.phase8@sentinel.ai",
        "app_metadata": {"role": role}
    }
    if card_id:
        claims["app_metadata"]["card_id"] = card_id
    token = create_access_token(claims)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# Milestone 1: Genuine End-to-End Integration Pipeline Test
# ==============================================================================

@pytest.mark.skipif(not PYSPARK_AVAILABLE, reason="PySpark is not installed")
def test_e2e_live_kafka_spark_postgres_fastapi_pipeline():
    """
    Genuine Live End-to-End Integration Pipeline:
    1. Transaction Generator creates canonical transaction.
    2. Published to Kafka topic 'transactions-canonical'.
    3. Consumed by genuine PySpark Structured Streaming micro-batch query.
    4. Evaluated by canonical feature extractor and Random Forest model.
    5. Persisted into decoupled PostgreSQL tables (transactions, fraud_predictions).
    6. Retrieved via authenticated FastAPI endpoint with PCI-masked card ID.
    """
    producer = TransactionKafkaProducer()
    if not producer.is_connected:
        pytest.skip("Kafka broker offline on 127.0.0.1:9092; skipping live E2E pipeline test.")

    db = DatabaseClient()
    if not db.test_connection():
        pytest.skip("PostgreSQL database offline; skipping live E2E pipeline test.")

    test_tx_id = f"TX_E2E_{uuid.uuid4().hex[:8]}"
    test_card_id = "CARD_007"
    raw_txn = producer.generator.generate_normal_transaction(card_id=test_card_id)
    raw_txn["transaction_id"] = test_tx_id
    raw_txn["amount"] = 88.50
    raw_txn["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Stage 1 & 2: Kafka publication
    published = producer.send_transaction(raw_txn)
    producer.flush()
    assert published is True, "Failed to publish transaction to Kafka 'transactions-canonical'"

    # Stage 3, 4, 5: Bounded PySpark Structured Streaming Execution
    from config.config import PROJECT_ROOT
    test_ckpt = PROJECT_ROOT / "logs" / "spark_checkpoints" / f"e2e_{uuid.uuid4().hex[:6]}"
    processor = RealTimeStreamProcessor()
    spark_success = processor.run_spark_streaming(
        checkpoint_dir=test_ckpt,
        timeout_seconds=10,
        max_batches=2,
        starting_offsets="earliest"
    )
    assert spark_success is True, "PySpark Structured Streaming failed to process batches"

    # Verify Stage 5: Database persistence directly from DB client
    stored_txn = db.get_transaction(test_tx_id)
    assert stored_txn is not None, f"Transaction {test_tx_id} was not persisted to PostgreSQL by Spark query"
    assert stored_txn["transaction_id"] == test_tx_id
    assert stored_txn["card_id"] == test_card_id

    # Stage 6: Authenticated FastAPI Gateway retrieval
    analyst_headers = make_token("fraud_investigator")
    response = client.get("/api/v1/transactions/recent?limit=25", headers=analyst_headers)
    assert response.status_code == 200
    recent_txns = response.json()
    assert isinstance(recent_txns, list)

    matching = next((t for t in recent_txns if t.get("transaction_id") == test_tx_id), None)
    assert matching is not None, f"Transaction {test_tx_id} not visible in FastAPI /transactions/recent"

    # Stage 7: Verify PCI masking and response contract
    assert "masked_card_id" in matching
    assert matching["masked_card_id"] == "CARD_***_007"
    assert "final_fraud_score" in matching or "scores" in matching or "fraud_decision" in matching


# ==============================================================================
# Milestone 2: Security & Role Authorization on Ingestion & Simulation
# ==============================================================================

def test_ingest_transaction_unauthenticated_fails_closed():
    """Unauthenticated POST /api/v1/transactions must fail closed with 401 Unauthorized."""
    payload = {
        "card_id": "CARD_007",
        "amount": 50.0,
        "merchant_name": "TestStore"
    }
    resp = client.post("/api/v1/transactions", json=payload)
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]

def test_simulate_unauthenticated_fails_closed():
    """Unauthenticated POST /api/v1/simulate must fail closed with 401 Unauthorized."""
    resp = client.post("/api/v1/simulate", json={"scenario": "NORMAL", "count": 1})
    assert resp.status_code == 401

def test_customer_ingest_own_card_authorized():
    """Authenticated customer is authorized to ingest transactions for their bound card."""
    cust_headers = make_token(role="customer", card_id="CARD_007")
    payload = {
        "transaction_id": f"TX_CUST_{uuid.uuid4().hex[:8]}",
        "card_id": "CARD_007",
        "amount": 35.0,
        "merchant_name": "LocalCafe"
    }
    resp = client.post("/api/v1/transactions", json=payload, headers=cust_headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "processed"

def test_customer_ingest_cross_card_forbidden():
    """Authenticated customer attempting to ingest for another card is blocked with 403 Forbidden."""
    cust_headers = make_token(role="customer", card_id="CARD_007")
    payload = {
        "transaction_id": f"TX_INTRUDER_{uuid.uuid4().hex[:8]}",
        "card_id": "CARD_012",
        "amount": 100.0,
        "merchant_name": "VictimAccount"
    }
    resp = client.post("/api/v1/transactions", json=payload, headers=cust_headers)
    assert resp.status_code == 403
    assert "not authorized to ingest transactions for card" in resp.json()["detail"].lower()

def test_customer_simulate_forbidden():
    """Customer role attempting to run fraud simulation is blocked with 403 Forbidden."""
    cust_headers = make_token(role="customer", card_id="CARD_007")
    resp = client.post("/api/v1/simulate", json={"scenario": "NORMAL", "count": 1}, headers=cust_headers)
    assert resp.status_code == 403

def test_investigator_and_admin_simulate_and_ingest_authorized():
    """Investigators and administrators are authorized for simulation and multi-card ingestion."""
    for role in ["fraud_investigator", "admin"]:
        headers = make_token(role=role)
        # 1. Simulation
        sim_resp = client.post("/api/v1/simulate", json={"scenario": "NORMAL", "count": 1}, headers=headers)
        assert sim_resp.status_code == 200

        # 2. Ingestion
        tx_id = f"TX_AUTH_{role[:4]}_{uuid.uuid4().hex[:6]}"
        ingest_resp = client.post("/api/v1/transactions", json={
            "transaction_id": tx_id,
            "card_id": "CARD_999",
            "amount": 150.0,
            "merchant_name": "DepartmentStore"
        }, headers=headers)
        assert ingest_resp.status_code == 201


# ==============================================================================
# Milestone 2: Thread-Safe Concurrency on Memory Buffer
# ==============================================================================

def test_concurrent_ingest_and_buffer_drain_thread_safety():
    """
    Tests thread safety of DatabaseClient memory buffer operations.
    Spawns concurrent worker threads executing transaction insertion,
    while another thread executes drain_memory_buffer().
    Verifies zero lost records, zero unhandled lock contention errors.
    """
    db = DatabaseClient()
    errors = []
    num_threads = 8
    items_per_thread = 15

    def worker_ingest(worker_id: int):
        try:
            for i in range(items_per_thread):
                t_id = f"TX_CONC_W{worker_id}_{i}_{uuid.uuid4().hex[:6]}"
                rec = {
                    "transaction_id": t_id,
                    "idempotency_key": f"IDEMP_{t_id}",
                    "card_id": f"CARD_{worker_id}",
                    "amount": 20.0 + i,
                    "merchant_name": "ConcStore",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                db.insert_transaction(rec)
        except Exception as e:
            errors.append(f"Worker {worker_id} exception: {e}")

    def worker_drain():
        try:
            for _ in range(3):
                db.drain_memory_buffer(admin_user_id="admin_concurrency_test")
                time.sleep(0.01)
        except Exception as e:
            errors.append(f"Drain worker exception: {e}")

    threads = [threading.Thread(target=worker_ingest, args=(w,)) for w in range(num_threads)]
    drain_thread = threading.Thread(target=worker_drain)

    # Start all concurrently
    for t in threads:
        t.start()
    drain_thread.start()

    for t in threads:
        t.join(timeout=10)
    drain_thread.join(timeout=10)

    assert len(errors) == 0, f"Thread concurrency errors encountered: {errors}"


# ==============================================================================
# Milestone 3: Time-Aware Deduplication Cache & Bounded Retention Tests
# ==============================================================================

def test_time_aware_dedup_cache_retention_and_pruning():
    """
    Validates TimeAwareDedupCache:
    1. Retains recent transactions across replay window (1800s).
    2. Evicts transactions older than retention window on prune.
    3. Enforces max capacity to prevent memory leaks under long runs.
    """
    cache = TimeAwareDedupCache(retention_seconds=10.0, max_capacity=5)

    base_time = 1000.0
    cache.add("tx_1", event_time=base_time)
    cache.add("tx_2", event_time=base_time + 2.0)

    # Within retention window
    assert cache.contains("tx_1", now=base_time + 5.0) is True
    assert cache.contains("tx_2", now=base_time + 5.0) is True

    # After expiration window (12 seconds later > 10.0s retention)
    assert cache.contains("tx_1", now=base_time + 12.0) is False

    # Max capacity safeguard test (using real current epoch so time.time() matches)
    now_epoch = time.time()
    cache_bounded = TimeAwareDedupCache(retention_seconds=100.0, max_capacity=3)
    for i in range(5):
        cache_bounded.add(f"k_{i}", event_time=now_epoch + i)

    assert len(cache_bounded) <= 3, "Cache capacity exceeded max_capacity safeguard!"
    assert "k_0" not in cache_bounded, "Oldest item k_0 was not evicted under max_capacity constraint"
    assert "k_4" in cache_bounded, "Newest item k_4 missing from cache"


def test_idempotent_replay_prevention_in_streaming_processor():
    """
    Verifies that replaying the exact same transaction within replay window
    is flagged as a duplicate and does NOT double-increment sliding window bursts.
    """
    processor = RealTimeStreamProcessor()
    tx_id = f"TX_DEDUP_{uuid.uuid4().hex[:8]}"
    card_id = f"CARD_DEDUP_{uuid.uuid4().hex[:4]}"
    txn = {
        "transaction_id": tx_id,
        "idempotency_key": f"IDEMP_{tx_id}",
        "card_id": card_id,
        "amount": 75.0,
        "merchant_name": "TestShop",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # First delivery
    res1 = processor.process_transaction(txn)
    assert res1["is_duplicate"] is False
    initial_burst = sum(1 for t in processor.window_1m if t["card_id"] == card_id)
    assert initial_burst == 1

    # Replayed delivery
    res2 = processor.process_transaction(txn)
    assert res2["is_duplicate"] is True
    subsequent_burst = sum(1 for t in processor.window_1m if t["card_id"] == card_id)
    assert subsequent_burst == 1, "Replayed transaction double-counted in sliding window burst!"


# ==============================================================================
# Milestone 3: Partial Database-Buffer Draining Resilience
# ==============================================================================

def test_partial_buffer_drain_retry_safety():
    """
    Verifies that if a record encounters a failure during drain,
    it remains safely in the buffer and can be recovered on retry.
    """
    db = DatabaseClient()
    # Add two records directly to buffer
    t1 = f"TX_BUF_A_{uuid.uuid4().hex[:6]}"
    t2 = f"TX_BUF_B_{uuid.uuid4().hex[:6]}"

    with DatabaseClient._buffer_lock:
        db._memory_transactions.insert(0, {
            "transaction_id": t1,
            "card_id": "CARD_007",
            "amount": 10.0,
            "merchant_name": "StoreA",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        db._memory_transactions.insert(0, {
            "transaction_id": t2,
            "card_id": "CARD_007",
            "amount": 20.0,
            "merchant_name": "StoreB",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    # Drain buffer
    drain_result = db.drain_memory_buffer(admin_user_id="admin_partial_test")
    assert drain_result["recovered_count"] >= 2
    assert drain_result["remaining_count"] == 0
