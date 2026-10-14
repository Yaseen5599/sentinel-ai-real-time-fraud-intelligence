"""
Unit tests for Behavioral Profile & Temporal Feature Extraction
"""

import pytest
from datetime import datetime, timedelta
from src.features.behavioral_features import CardBehaviorProfile

def test_temporal_causality():
    """Verify that features only consider past transactions strictly before current transaction."""
    profile = CardBehaviorProfile("CARD_TEST")
    t0 = datetime(2026, 9, 28, 10, 0, 0)

    # 3 historical transactions
    profile.update({"card_id": "CARD_TEST", "amount": 100.0, "timestamp": (t0 - timedelta(hours=3)).isoformat(), "merchant": "ShopA", "location": "New York"})
    profile.update({"card_id": "CARD_TEST", "amount": 50.0, "timestamp": (t0 - timedelta(hours=2)).isoformat(), "merchant": "ShopB", "location": "New York"})
    profile.update({"card_id": "CARD_TEST", "amount": 150.0, "timestamp": (t0 - timedelta(hours=1)).isoformat(), "merchant": "ShopA", "location": "New York"})

    # Current transaction at t0
    current_txn = {
        "card_id": "CARD_TEST",
        "amount": 200.0,
        "timestamp": t0.isoformat(),
        "merchant": "ShopA",
        "location": "New York"
    }

    features = profile.get_features_for_transaction(current_txn)

    # Average should be based only on past 3: (100 + 50 + 150) / 3 = 100.0
    assert features["avg_amount"] == 100.0
    # Amount ratio: 200 / 100 = 2.0
    assert features["amount_ratio"] == 2.0
    # Location should not be unusual
    assert not features["is_unusual_location"]
    # Merchant ShopA was seen twice, so frequent
    assert not features["is_unusual_merchant"]

def test_cold_start():
    """Verify clean baseline behavior for brand-new card with no prior history."""
    profile = CardBehaviorProfile("CARD_NEW")
    current_txn = {
        "card_id": "CARD_NEW",
        "amount": 85.0,
        "timestamp": datetime.now().isoformat(),
        "merchant": "Amazon",
        "location": "Boston"
    }
    features = profile.get_features_for_transaction(current_txn)
    assert features["avg_amount"] == 85.0
    assert features["amount_ratio"] == 1.0
    assert features["txns_last_5min"] == 1
