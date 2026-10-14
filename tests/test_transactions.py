"""
Unit tests for Transaction Parsing, Validation, and Scenario Generation
"""

import pytest
import json
from src.producer.transaction_generator import TransactionGenerator

@pytest.fixture
def generator():
    return TransactionGenerator()

def test_normal_transaction_schema(generator):
    txn = generator.generate_normal_transaction()
    required_fields = ["transaction_id", "card_id", "amount", "merchant", "location", "timestamp", "status"]
    for field in required_fields:
        assert field in txn, f"Missing required field: {field}"
    assert isinstance(txn["amount"], float)
    assert txn["amount"] > 0

def test_json_serialization(generator):
    txn = generator.generate_normal_transaction()
    serialized = json.dumps(txn)
    deserialized = json.loads(serialized)
    assert deserialized["transaction_id"] == txn["transaction_id"]
    assert deserialized["amount"] == txn["amount"]

def test_rapid_burst_scenario(generator):
    txns = generator.generate_scenario_rapid_burst("CARD_007", count=6)
    assert len(txns) == 6
    assert all(t["card_id"] == "CARD_007" for t in txns)
    assert all(t["scenario"] == "RAPID_TRANSACTION_BURST" for t in txns)

def test_impossible_travel_scenario(generator):
    txns = generator.generate_scenario_impossible_travel("CARD_012")
    assert len(txns) == 2
    assert txns[0]["location"] != txns[1]["location"]
