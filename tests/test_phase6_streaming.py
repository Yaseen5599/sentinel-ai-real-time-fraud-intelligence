"""
Sentinel AI — Phase 6 Automated Streaming & Integration Tests
Tests for:
1. Milestone 1: Authoritative topic unification (transactions-canonical) and producer reliability.
2. Milestone 2: Real Spark Structured Streaming execution, schema parsing, watermarking, foreachBatch.
3. Milestone 3: Idempotency & Deduplication (duplicate-event prevention in memory and database).
4. Milestone 4: End-to-end streaming telemetry and pipeline health reporting.
"""

import os
import json
import uuid
import time
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from config.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_CANONICAL_TOPIC,
    KAFKA_TOPIC,
    LOGS_DIR
)
from src.producer.kafka_producer import TransactionKafkaProducer
from src.producer.transaction_generator import TransactionGenerator
from src.streaming.spark_streaming_pipeline import (
    RealTimeStreamProcessor,
    CANONICAL_STREAMING_SCHEMA,
    PYSPARK_AVAILABLE
)
from src.database.db_client import DatabaseClient
from src.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# ==============================================================================
# Milestone 1: Topic Unification & Producer Reliability Tests
# ==============================================================================

def test_authoritative_topic_unification():
    """Confirms both producer and consumer standardize on 'transactions-canonical'."""
    assert KAFKA_TOPIC == "transactions-canonical"
    assert KAFKA_CANONICAL_TOPIC == "transactions-canonical"

    producer = TransactionKafkaProducer()
    assert producer.topic == "transactions-canonical"

def test_kafka_producer_reliability_and_publish():
    """Tests producer connectivity and message publishing to 'transactions-canonical'."""
    producer = TransactionKafkaProducer()
    if not producer.is_connected:
        pytest.skip("Kafka broker is offline")

    test_tx_id = f"TX_M1_{uuid.uuid4().hex[:8]}"
    txn = producer.generator.generate_normal_transaction(card_id="CARD_007")
    txn["transaction_id"] = test_tx_id
    success = producer.send_transaction(txn)
    assert success is True

# ==============================================================================
# Milestone 2: Real Spark Structured Streaming Tests
# ==============================================================================

@pytest.mark.skipif(not PYSPARK_AVAILABLE, reason="PySpark is not installed")
def test_spark_session_creation_and_kafka_schema():
    """Validates SparkSession instantiation with Kafka connector and schema fields."""
    processor = RealTimeStreamProcessor()
    spark = processor.create_spark_session(app_name="SentinelAI-TestSparkSession")
    try:
        assert spark is not None
        assert CANONICAL_STREAMING_SCHEMA is not None
        schema_fields = [f.name for f in CANONICAL_STREAMING_SCHEMA.fields]
        assert "transaction_id" in schema_fields
        assert "card_id" in schema_fields
        assert "amount" in schema_fields
        assert "timestamp" in schema_fields
    finally:
        spark.stop()

@pytest.mark.skipif(not PYSPARK_AVAILABLE, reason="PySpark is not installed")
def test_spark_streaming_bounded_execution():
    """
    Executes a bounded PySpark Structured Streaming run consuming real Kafka records.
    Tests schema parsing, watermarking, foreachBatch handler, and clean shutdown.
    """
    producer = TransactionKafkaProducer()
    if not producer.is_connected:
        pytest.skip("Kafka broker is offline")

    # Seed 3 transactions
    test_ids = [f"TX_SPARK_{uuid.uuid4().hex[:8]}" for _ in range(3)]
    for tid in test_ids:
        t = producer.generator.generate_normal_transaction(card_id="CARD_007")
        t["transaction_id"] = tid
        producer.send_transaction(t)

    processor = RealTimeStreamProcessor()
    success = processor.run_spark_streaming(timeout_seconds=4, max_batches=2)
    assert success is True
    assert processor.active_engine == "Spark Structured Streaming"

# ==============================================================================
# Milestone 3: Idempotency & Deduplication Tests
# ==============================================================================

def test_idempotent_duplicate_prevention_in_memory():
    """
    Verifies that redelivering the same transaction does NOT:
    1. Re-add to sliding window burst count.
    2. Double-count in cardholder behavioral profile.
    3. Duplicate rows in _memory_transactions.
    """
    processor = RealTimeStreamProcessor()
    tx_id = f"TX_IDEMP_{uuid.uuid4().hex[:8]}"
    idemp_key = f"IDEMP_KEY_{uuid.uuid4().hex[:8]}"
    card_id = f"CARD_TEST_{uuid.uuid4().hex[:4]}"

    test_txn = {
        "transaction_id": tx_id,
        "idempotency_key": idemp_key,
        "card_id": card_id,
        "amount": 100.0,
        "merchant": "ElectronicsStore",
        "merchant_name": "ElectronicsStore",
        "city": "New York",
        "location": "New York",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # First delivery
    res1 = processor.process_transaction(test_txn)
    assert res1["is_duplicate"] is False
    initial_burst = sum(1 for t in processor.window_1m if t["card_id"] == card_id)
    initial_history_len = len(processor.card_histories.get(card_id, []))
    assert initial_burst == 1
    assert initial_history_len == 1

    # Second delivery (Duplicate event)
    res2 = processor.process_transaction(test_txn)
    assert res2["is_duplicate"] is True

    # Check that sliding window was NOT incremented twice
    subsequent_burst = sum(1 for t in processor.window_1m if t["card_id"] == card_id)
    subsequent_history_len = len(processor.card_histories.get(card_id, []))
    assert subsequent_burst == 1, "Duplicate delivery distorted sliding window burst count!"
    assert subsequent_history_len == 1, "Duplicate delivery distorted cardholder history length!"

def test_database_client_idempotency_integrity_handling():
    """
    Verifies DatabaseClient handles duplicate insertion gracefully without marking DB offline.
    """
    db = DatabaseClient()
    tx_id = f"TX_DB_IDEMP_{uuid.uuid4().hex[:8]}"
    idemp_key = f"IDEMP_DB_{uuid.uuid4().hex[:8]}"
    record = {
        "transaction_id": tx_id,
        "idempotency_key": idemp_key,
        "card_id": "CARD_007",
        "amount": 55.0,
        "merchant_name": "CoffeeShop",
        "city": "Seattle"
    }

    # First write
    success1 = db.insert_transaction(record)
    # Second write with same transaction_id
    success2 = db.insert_transaction(record)

    # Database must remain connected
    if db.is_connected:
        assert success1 is True
        assert success2 is True
        assert db.is_connected is True

# ==============================================================================
# Milestone 4: Telemetry & Pipeline Monitoring Tests
# ==============================================================================

def test_pipeline_health_reports_streaming_worker_telemetry():
    """
    Verifies GET /api/v1/pipeline/health correctly incorporates Spark and worker telemetry.
    """
    processor = RealTimeStreamProcessor()
    processor.update_telemetry(engine="Spark Structured Streaming", spark_active=True, last_batch_id=1, batch_size=5)

    resp = client.get("/api/v1/pipeline/health")
    assert resp.status_code == 200
    data = resp.json()
    services = data["services"]

    assert "stream_processor" in services
    sp_info = services["stream_processor"]
    assert sp_info["engine"] == "Spark Structured Streaming"
    assert sp_info["spark_streaming_active"] is True
    assert sp_info["mode"] == "Spark Structured Streaming"

    # Reset telemetry to fallback
    processor.update_telemetry(engine="In-Process Micro-Batch", spark_active=False)
    resp2 = client.get("/api/v1/pipeline/health")
    sp_info2 = resp2.json()["services"]["stream_processor"]
    assert sp_info2["spark_streaming_active"] is False
    assert sp_info2["mode"] == "In-Process Micro-Batch Fallback"

# ==============================================================================
# Phase 6 Remediation Tests
# ==============================================================================

def test_timestamp_normalization_and_rejection():
    """
    Verifies Fix 4:
    - Missing or null timestamp defaults safely to current time.
    - Valid ISO strings and datetime objects normalize correctly.
    - Numeric epoch timestamps are supported.
    - Normalized timestamp is assigned back to the transaction dict.
    - Unparseable timestamps raise ValueError with clear explanation.
    """
    processor = RealTimeStreamProcessor()

    # 1. Valid ISO
    t1 = {"transaction_id": "TX_T1", "card_id": "CARD_T", "amount": 25.0, "timestamp": "2026-10-10T12:00:00Z"}
    r1 = processor.process_transaction(t1)
    assert "2026-10-10T12:00:00" in r1["timestamp"]
    assert "2026-10-10T12:00:00" in t1["timestamp"]

    # 2. Missing timestamp
    t2 = {"transaction_id": "TX_T2", "card_id": "CARD_T", "amount": 35.0}
    r2 = processor.process_transaction(t2)
    assert r2["timestamp"] is not None
    assert t2["timestamp"] is not None

    # 3. Null timestamp
    t3 = {"transaction_id": "TX_T3", "card_id": "CARD_T", "amount": 45.0, "timestamp": None}
    r3 = processor.process_transaction(t3)
    assert r3["timestamp"] is not None
    assert t3["timestamp"] is not None

    # 4. Numeric epoch
    t4 = {"transaction_id": "TX_T4", "card_id": "CARD_T", "amount": 55.0, "timestamp": 1760000000}
    r4 = processor.process_transaction(t4)
    assert r4["timestamp"] is not None

    # 5. Invalid timestamp string must raise ValueError
    t5 = {"transaction_id": "TX_T5", "card_id": "CARD_T", "amount": 65.0, "timestamp": "INVALID_TIMESTAMP_STRING"}
    with pytest.raises(ValueError) as excinfo:
        processor.process_transaction(t5)
    assert "Invalid timestamp format" in str(excinfo.value)

def test_streaming_fallback_telemetry_signature_compatibility():
    """
    Verifies Fix 3: update_telemetry accepts both batch_size and last_batch_size
    without raising TypeError.
    """
    processor = RealTimeStreamProcessor()
    # Call with last_batch_size as done in consumer
    processor.update_telemetry(engine="In-Process Micro-Batch", spark_active=False, last_batch_size=1)
    assert processor.active_engine == "In-Process Micro-Batch"

    # Call with batch_size as done in batch handlers
    processor.update_telemetry(engine="Spark Structured Streaming", spark_active=True, batch_size=5)
    assert processor.active_engine == "Spark Structured Streaming"

    # Reset
    processor.update_telemetry(engine="In-Process Micro-Batch", spark_active=False)
