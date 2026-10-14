"""
Unit Tests for Canonical Feature Parity & Point-in-Time Causality
Asserts mathematical consistency, cold-start fallbacks, Haversine physics,
and strict temporal causality.
"""

import math
from datetime import datetime, timedelta, timezone
from src.features.canonical_features import (
    CanonicalFeatureExtractor,
    haversine_distance_km,
    CANONICAL_FEATURE_NAMES
)

def test_haversine_distance_accuracy():
    # New York (40.7128, -74.0060) to London (51.5074, -0.1278) ~5570 km
    ny_lat, ny_lon = 40.7128, -74.0060
    lon_lat, lon_lon = 51.5074, -0.1278
    dist = haversine_distance_km(ny_lat, ny_lon, lon_lat, lon_lon)
    assert 5500.0 < dist < 5600.0

    # Same location distance is zero
    assert haversine_distance_km(ny_lat, ny_lon, ny_lat, ny_lon) == 0.0

def test_diurnal_cyclical_encoding():
    extractor = CanonicalFeatureExtractor()
    t_noon = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    txn = {
        "amount": 50.0,
        "timestamp": t_noon.isoformat(),
        "card_id": "CARD_001"
    }
    feats = extractor.extract_features(txn)
    # At 12:00, 2*pi*(12/24) = pi. sin(pi) ~ 0, cos(pi) ~ -1
    assert abs(feats["hour_sin"]) < 0.01
    assert abs(feats["hour_cos"] - (-1.0)) < 0.01
    # Check unit circle property
    assert abs((feats["hour_sin"] ** 2 + feats["hour_cos"] ** 2) - 1.0) < 0.01

def test_cold_start_fallback():
    extractor = CanonicalFeatureExtractor()
    t0 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    txn = {
        "amount": 75.0,
        "timestamp": t0.isoformat(),
        "card_id": "CARD_FIRST_SEEN"
    }
    # No history and no baseline
    feats = extractor.extract_features(txn, card_history=[], card_baseline=None)
    assert feats["amount"] == 75.0
    assert feats["velocity_1m"] == 0.0
    assert feats["velocity_5m"] == 0.0
    assert feats["velocity_24h"] == 0.0
    assert feats["distance_from_last_km"] == 0.0
    assert feats["speed_kmh"] == 0.0
    assert feats["is_new_merchant"] == 0.0

def test_strict_temporal_causality():
    extractor = CanonicalFeatureExtractor()
    t_past = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t_now = datetime(2026, 9, 1, 10, 2, 0, tzinfo=timezone.utc)
    t_future = datetime(2026, 9, 1, 10, 5, 0, tzinfo=timezone.utc)

    history = [
        {"timestamp": t_past.isoformat(), "amount": 50.0, "city": "Chicago", "latitude": 41.8781, "longitude": -87.6298},
        {"timestamp": t_future.isoformat(), "amount": 1000.0, "city": "Tokyo"} # Future event must be ignored!
    ]

    current_txn = {
        "amount": 60.0,
        "timestamp": t_now.isoformat(),
        "card_id": "CARD_002",
        "city": "Chicago",
        "latitude": 41.8781,
        "longitude": -87.6298
    }

    feats = extractor.extract_features(current_txn, card_history=history)

    # Velocity in last 5m should only count t_past (1 event), ignoring t_future
    assert feats["velocity_5m"] == 1.0
    # 24h spend should only include $50, not $1000 from the future
    assert feats["spend_velocity_24h"] == 50.0

def test_feature_vector_dimension():
    extractor = CanonicalFeatureExtractor()
    txn = {"amount": 50.0, "timestamp": datetime.now(timezone.utc).isoformat()}
    feats = extractor.extract_features(txn)
    vec = extractor.to_feature_vector(feats)
    assert len(vec) == 18
    assert len(CANONICAL_FEATURE_NAMES) == 18
