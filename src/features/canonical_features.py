"""
Sentinel AI — Canonical Feature Extraction Pipeline
Defines identical feature transformations for both offline model training (batch)
and real-time streaming inference (zero train-serve skew).
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from src.producer.transaction_generator import CITY_COORDINATES, MERCHANT_CATALOG
# High-risk Merchant Category Codes (MCC)
MCC_RISK_MAP = {
    "5944": 0.85,  # Jewelry Stores
    "7995": 0.95,  # Betting / Casino / Gambling
    "6051": 0.90,  # Crypto / Quasi-Cash / Foreign Currency
    "5732": 0.65,  # Electronic Sales
    "4829": 0.75,  # Wire Transfer / Money Orders
    "5411": 0.10,  # Grocery Stores / Supermarkets
    "5814": 0.15,  # Fast Food Restaurants
    "5541": 0.20,  # Service Stations (Fuel)
    "5311": 0.25,  # Department Stores
    "4121": 0.20,  # Taxicabs and Limousines (Uber/Lyft)
}

CHANNEL_RISK_MAP = {
    "IN_PERSON_CHIP": 0.10,
    "IN_PERSON_CONTACTLESS": 0.15,
    "ONLINE_ECOMMERCE": 0.60,
    "ATM_WITHDRAWAL": 0.40,
    "PHONE_MOTO": 0.70
}

CANONICAL_FEATURE_NAMES = [
    "amount",
    "log_amount",
    "hour_sin",
    "hour_cos",
    "day_of_week",
    "is_weekend",
    "velocity_1m",
    "velocity_5m",
    "velocity_24h",
    "spend_velocity_24h",
    "amount_to_avg_ratio",
    "amount_z_score",
    "distance_from_last_km",
    "speed_kmh",
    "is_new_merchant",
    "is_new_location",
    "mcc_risk_weight",
    "channel_risk_weight"
]

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance in kilometers using the Haversine formula."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c

class CanonicalFeatureExtractor:
    """
    Extracts canonical features from a transaction event given historical cardholder context.
    Ensures 100% mathematical parity across training and inference.
    """

    def __init__(self):
        self.feature_names = list(CANONICAL_FEATURE_NAMES)

    def extract_features(self,
                         txn: Dict[str, Any],
                         card_history: Optional[List[Dict[str, Any]]] = None,
                         card_baseline: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Derives all 18 canonical features respecting temporal causality (strictly past events).
        """
        amount = float(txn.get("amount", 0.0))
        log_amount = round(math.log1p(max(0.0, amount)), 4)

        raw_ts = txn.get("timestamp")
        if isinstance(raw_ts, str):
            try:
                ts = datetime.fromisoformat(raw_ts)
            except Exception:
                ts = datetime.now(timezone.utc)
        elif isinstance(raw_ts, datetime):
            ts = raw_ts
        else:
            ts = datetime.now(timezone.utc)

        # Diurnal temporal encodings
        hour = ts.hour + (ts.minute / 60.0)
        hour_sin = round(math.sin(2.0 * math.pi * hour / 24.0), 4)
        hour_cos = round(math.cos(2.0 * math.pi * hour / 24.0), 4)
        day_of_week = float(ts.weekday())
        is_weekend = 1.0 if day_of_week in [5, 6] else 0.0

        # Helper to extract city and coordinates from transaction
        def resolve_loc_coords(t_dict: Dict[str, Any]) -> Tuple[str, Optional[float], Optional[float]]:
            c = t_dict.get("city", "")
            if not c:
                loc_val = t_dict.get("location")
                if isinstance(loc_val, str):
                    c = loc_val
                elif isinstance(loc_val, dict):
                    c = loc_val.get("city", "")

            lat_val = t_dict.get("latitude")
            lon_val = t_dict.get("longitude")
            if (lat_val is None or lon_val is None) and isinstance(t_dict.get("location"), dict):
                lat_val = t_dict["location"].get("latitude")
                lon_val = t_dict["location"].get("longitude")

            if (lat_val is None or lon_val is None) and c in CITY_COORDINATES:
                lat_val = CITY_COORDINATES[c]["lat"]
                lon_val = CITY_COORDINATES[c]["lon"]

            return c, lat_val, lon_val

        current_city, curr_lat, curr_lon = resolve_loc_coords(txn)
        current_merchant = txn.get("merchant_name", txn.get("merchant", ""))
        merch_meta = MERCHANT_CATALOG.get(current_merchant, {})

        # MCC and Channel risk weights
        mcc = str(txn.get("merchant_category_code", txn.get("mcc", "")))
        if not mcc or mcc == "5411":
            if merch_meta.get("mcc"):
                mcc = merch_meta["mcc"]
            elif not mcc:
                mcc = "5411"
        mcc_risk_weight = MCC_RISK_MAP.get(mcc, 0.30)

        channel = str(txn.get("channel", ""))
        if not channel:
            channel = merch_meta.get("channel", "ONLINE_ECOMMERCE")
        channel_risk_weight = CHANNEL_RISK_MAP.get(channel, 0.40)

        # Filter card history strictly prior to current transaction
        past_txns = []
        if card_history:
            for t in card_history:
                t_raw_ts = t.get("timestamp")
                if isinstance(t_raw_ts, str):
                    try:
                        t_ts = datetime.fromisoformat(t_raw_ts)
                    except Exception:
                        continue
                elif isinstance(t_raw_ts, datetime):
                    t_ts = t_raw_ts
                else:
                    continue

                if t_ts < ts:
                    past_txns.append((t_ts, t))

        # Baseline statistics
        if card_baseline:
            avg_amount = float(card_baseline.get("baseline_avg_amount", 75.0))
            std_amount = float(card_baseline.get("baseline_std_amount", 35.0))
        elif past_txns:
            past_amts = [float(t[1].get("amount", 0.0)) for t in past_txns]
            avg_amount = float(np.mean(past_amts))
            std_amount = float(np.std(past_amts)) if len(past_amts) > 1 else max(avg_amount * 0.4, 5.0)
        else:
            avg_amount = max(amount, 50.0)
            std_amount = max(avg_amount * 0.4, 15.0)

        amount_to_avg_ratio = round(amount / max(avg_amount, 1.0), 4)
        amount_z_score = round((amount - avg_amount) / max(std_amount, 1.0), 4)

        # Velocity calculations
        velocity_1m = 0.0
        velocity_5m = 0.0
        velocity_24h = 0.0
        spend_velocity_24h = 0.0

        for past_time, past_t in past_txns:
            delta_sec = (ts - past_time).total_seconds()
            if delta_sec <= 60.0:
                velocity_1m += 1.0
            if delta_sec <= 300.0:
                velocity_5m += 1.0
            if delta_sec <= 86400.0:
                velocity_24h += 1.0
                spend_velocity_24h += float(past_t.get("amount", 0.0))

        spend_velocity_24h = round(spend_velocity_24h, 2)

        # Distance and Speed calculations
        distance_from_last_km = 0.0
        speed_kmh = 0.0

        if past_txns and curr_lat is not None and curr_lon is not None:
            last_ts, last_t = sorted(past_txns, key=lambda x: x[0])[-1]
            _, last_lat, last_lon = resolve_loc_coords(last_t)

            if last_lat is not None and last_lon is not None:
                dist = haversine_distance_km(last_lat, last_lon, curr_lat, curr_lon)
                time_delta_hours = max((ts - last_ts).total_seconds() / 3600.0, 1.0 / 3600.0)
                distance_from_last_km = round(dist, 2)
                speed_kmh = round(dist / time_delta_hours, 2)

        # Familiarity features
        past_merchants = {t[1].get("merchant_name", t[1].get("merchant", "")) for t in past_txns}
        past_cities = {resolve_loc_coords(t[1])[0] for t in past_txns}

        is_new_merchant = 1.0 if (past_txns and current_merchant and current_merchant not in past_merchants) else 0.0
        is_new_location = 1.0 if (past_txns and current_city and current_city not in past_cities) else 0.0

        return {
            "amount": amount,
            "log_amount": log_amount,
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "velocity_1m": velocity_1m,
            "velocity_5m": velocity_5m,
            "velocity_24h": velocity_24h,
            "spend_velocity_24h": spend_velocity_24h,
            "amount_to_avg_ratio": amount_to_avg_ratio,
            "amount_z_score": amount_z_score,
            "distance_from_last_km": distance_from_last_km,
            "speed_kmh": speed_kmh,
            "is_new_merchant": is_new_merchant,
            "is_new_location": is_new_location,
            "mcc_risk_weight": mcc_risk_weight,
            "channel_risk_weight": channel_risk_weight
        }

    def to_feature_vector(self, feature_dict: Dict[str, float]) -> np.ndarray:
        """Converts extracted feature dictionary to an ordered 1D numpy array."""
        return np.array([feature_dict[col] for col in self.feature_names], dtype=np.float64)
