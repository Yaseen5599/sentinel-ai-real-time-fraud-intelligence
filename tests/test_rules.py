"""
Unit tests for the 7 Fraud Detection Rules
"""

import pytest
from datetime import datetime, timedelta
from src.rules.fraud_rules import FraudRuleEngine

@pytest.fixture
def engine():
    return FraudRuleEngine()

def test_rule_1_burst_txns(engine):
    """Rule 1: More than 5 transactions within 2 minutes."""
    now = datetime.now()
    history = [
        {"card_id": "CARD_01", "timestamp": (now - timedelta(seconds=i * 15)).isoformat(), "status": "SUCCESS"}
        for i in range(1, 7)  # 6 past txns within 90 seconds
    ]
    txn = {
        "card_id": "CARD_01",
        "amount": 50.0,
        "timestamp": now.isoformat(),
        "status": "SUCCESS"
    }
    score, rules, explanations = engine.evaluate(txn, history)
    assert "RULE_1_BURST_TXNS" in rules
    assert score >= 0.20
    assert any("2 minutes" in exp for exp in explanations)

def test_rule_2_impossible_travel(engine):
    """Rule 2: Geographically distant locations in short window."""
    now = datetime.now()
    history = [
        {"card_id": "CARD_02", "timestamp": (now - timedelta(minutes=10)).isoformat(), "location": "New York", "status": "SUCCESS"}
    ]
    txn = {
        "card_id": "CARD_02",
        "amount": 100.0,
        "timestamp": now.isoformat(),
        "location": "London",
        "status": "SUCCESS"
    }
    score, rules, explanations = engine.evaluate(txn, history)
    assert "RULE_2_IMPOSSIBLE_TRAVEL" in rules
    assert any("Impossible travel" in exp for exp in explanations)

def test_rule_3_high_amount_multiple(engine):
    """Rule 3: Amount > 3x customer average."""
    now = datetime.now()
    txn = {
        "card_id": "CARD_03",
        "amount": 500.0,
        "avg_amount": 100.0,
        "timestamp": now.isoformat(),
        "status": "SUCCESS"
    }
    score, rules, explanations = engine.evaluate(txn, [])
    assert "RULE_3_HIGH_AMOUNT_MULTIPLE" in rules
    assert any("5.0x" in exp for exp in explanations)

def test_rule_4_new_merchant_high_amount(engine):
    """Rule 4: New merchant combined with unusually high amount (>2x avg)."""
    now = datetime.now()
    txn = {
        "card_id": "CARD_04",
        "merchant": "CryptoExchange",
        "frequent_merchants": ["Amazon", "Target"],
        "amount": 350.0,
        "avg_amount": 100.0,
        "timestamp": now.isoformat(),
        "status": "SUCCESS"
    }
    score, rules, explanations = engine.evaluate(txn, [])
    assert "RULE_4_NEW_MERCHANT_HIGH_AMOUNT" in rules

def test_rule_5_declined_followed_by_success(engine):
    """Rule 5: Declined txns followed by successful high-value txn."""
    now = datetime.now()
    history = [
        {"card_id": "CARD_05", "timestamp": (now - timedelta(minutes=3)).isoformat(), "status": "DECLINED"},
        {"card_id": "CARD_05", "timestamp": (now - timedelta(minutes=1)).isoformat(), "status": "DECLINED"}
    ]
    txn = {
        "card_id": "CARD_05",
        "amount": 250.0,
        "avg_amount": 100.0,
        "timestamp": now.isoformat(),
        "status": "SUCCESS"
    }
    score, rules, explanations = engine.evaluate(txn, history)
    assert "RULE_5_DECLINED_FOLLOWED_BY_SUCCESS" in rules

def test_rule_6_merchant_card_swarm(engine):
    """Rule 6: Multiple distinct cards at same merchant in short time."""
    now = datetime.now()
    merchant_history = [
        {"card_id": "CARD_01", "timestamp": (now - timedelta(minutes=1)).isoformat()},
        {"card_id": "CARD_02", "timestamp": (now - timedelta(minutes=2)).isoformat()},
        {"card_id": "CARD_03", "timestamp": (now - timedelta(minutes=3)).isoformat()}
    ]
    txn = {
        "card_id": "CARD_04",
        "merchant": "ElectronicsHub",
        "amount": 80.0,
        "timestamp": now.isoformat(),
        "status": "SUCCESS"
    }
    score, rules, explanations = engine.evaluate(txn, [], merchant_history=merchant_history)
    assert "RULE_6_MERCHANT_CARD_SWARM" in rules

def test_rule_7_unusual_time(engine):
    """Rule 7: Transaction at unusual hour for that customer."""
    night_time = datetime.now().replace(hour=3, minute=0, second=0)
    txn = {
        "card_id": "CARD_07",
        "amount": 50.0,
        "usual_hours": list(range(8, 22)),  # 8 AM to 10 PM
        "timestamp": night_time.isoformat(),
        "status": "SUCCESS"
    }
    score, rules, explanations = engine.evaluate(txn, [])
    assert "RULE_7_UNUSUAL_TIME" in rules
