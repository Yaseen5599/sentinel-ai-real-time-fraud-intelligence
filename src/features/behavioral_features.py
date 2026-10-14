"""
Personalized Behavioral Baseline & Feature Extraction
Computes cardholder-specific historical profiles and real-time streaming behavioral features
respecting temporal causality (only past transactions up to the current one are used).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np

class CardBehaviorProfile:
    """
    Maintains and calculates personalized behavioral features for an individual card.
    """
    def __init__(self, card_id: str):
        self.card_id = card_id
        self.history: List[Dict[str, Any]] = []

    def update(self, txn: Dict[str, Any]):
        """Append transaction to card history keeping chronological order."""
        self.history.append(txn)
        # Keep recent history manageable (e.g. last 1000 txns)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

    def get_features_for_transaction(self, current_txn: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract behavioral baseline and instantaneous streaming features
        using ONLY history prior to or at current_txn.
        """
        current_time = current_txn.get("timestamp")
        if isinstance(current_time, str):
            try:
                current_time = datetime.fromisoformat(current_time.replace("Z", "+00:00"))
            except Exception:
                current_time = datetime.now(timezone.utc)
        elif not isinstance(current_time, datetime):
            current_time = datetime.now(timezone.utc)
        current_amount = float(current_txn.get("amount", 0.0))
        current_merchant = current_txn.get("merchant_name") or current_txn.get("merchant", "")
        current_location = current_txn.get("city") or current_txn.get("location", "")

        # Past transactions strictly before current_time
        past_txns = [
            t for t in self.history
            if (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]) < current_time
        ]

        if not past_txns:
            # Baseline for cold start (first seen card)
            return {
                "avg_amount": current_amount,
                "max_normal_amount": current_amount * 1.5,
                "amount_ratio": 1.0,
                "usual_hours": [current_time.hour],
                "is_unusual_hour": False,
                "frequent_merchants": [current_merchant],
                "is_unusual_merchant": False,
                "frequent_locations": [current_location],
                "is_unusual_location": False,
                "txns_last_5min": 1,
                "distinct_locations_last_1h": 1,
                "avg_time_gap_seconds": 3600.0,
                "daily_spend_last_24h": current_amount,
                "typical_daily_spending": current_amount
            }

        # 1. Amount behavior
        past_amounts = [float(t.get("amount", 0.0)) for t in past_txns]
        avg_amount = float(np.mean(past_amounts))
        std_amount = float(np.std(past_amounts)) if len(past_amounts) > 1 else avg_amount * 0.5
        max_normal_amount = avg_amount + 2.5 * std_amount
        amount_ratio = current_amount / max(avg_amount, 1.0)

        # 2. Timing behavior
        past_hours = [
            (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]).hour
            for t in past_txns
        ]
        # Active hours are hours with at least 1 txn or +/- 1 hour margin
        usual_hours = sorted(list(set(past_hours)))
        is_unusual_hour = current_time.hour not in usual_hours and len(usual_hours) >= 5

        # 3. Merchant behavior
        past_merchants = [t.get("merchant", "") for t in past_txns if t.get("merchant")]
        merchant_counts: Dict[str, int] = {}
        for m in past_merchants:
            merchant_counts[m] = merchant_counts.get(m, 0) + 1
        # Frequent merchants: used at least twice or top 3
        sorted_merchants = sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)
        frequent_merchants = [m for m, c in sorted_merchants[:5]]
        is_unusual_merchant = current_merchant not in frequent_merchants if len(frequent_merchants) > 0 else False

        # 4. Location behavior
        past_locations = [t.get("location", "") for t in past_txns if t.get("location")]
        location_counts: Dict[str, int] = {}
        for l in past_locations:
            location_counts[l] = location_counts.get(l, 0) + 1
        sorted_locs = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)
        frequent_locations = [l for l, c in sorted_locs[:3]]
        is_unusual_location = current_location not in frequent_locations if len(frequent_locations) > 0 else False

        # 5. Velocity: Txns in last 5 minutes
        five_mins_ago = current_time - timedelta(minutes=5)
        txns_last_5min = 1 + sum(
            1 for t in past_txns
            if (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]) >= five_mins_ago
        )

        # 6. Geographic diversity: Distinct locations in last 1 hour
        one_hour_ago = current_time - timedelta(hours=1)
        recent_1h_locs = set(
            t.get("location") for t in past_txns
            if (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]) >= one_hour_ago
        )
        recent_1h_locs.add(current_location)
        distinct_locations_last_1h = len(recent_1h_locs)

        # 7. Average time gap between transactions (seconds)
        past_times = sorted([
            datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]
            for t in past_txns
        ])
        if len(past_times) >= 2:
            gaps = [(past_times[i] - past_times[i-1]).total_seconds() for i in range(1, len(past_times))]
            avg_time_gap_seconds = float(np.mean(gaps))
        else:
            avg_time_gap_seconds = 3600.0

        # 8. Spending velocity: Daily spend in last 24 hours
        one_day_ago = current_time - timedelta(hours=24)
        daily_spend_last_24h = current_amount + sum(
            float(t.get("amount", 0.0)) for t in past_txns
            if (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]) >= one_day_ago
        )
        # Typical daily spending (total past spend / span in days, min 1)
        first_time = past_times[0]
        days_span = max(1.0, (current_time - first_time).total_seconds() / 86400.0)
        typical_daily_spending = sum(past_amounts) / days_span

        return {
            "avg_amount": round(avg_amount, 2),
            "max_normal_amount": round(max_normal_amount, 2),
            "amount_ratio": round(amount_ratio, 2),
            "usual_hours": usual_hours,
            "is_unusual_hour": is_unusual_hour,
            "frequent_merchants": frequent_merchants,
            "is_unusual_merchant": is_unusual_merchant,
            "frequent_locations": frequent_locations,
            "is_unusual_location": is_unusual_location,
            "txns_last_5min": txns_last_5min,
            "distinct_locations_last_1h": distinct_locations_last_1h,
            "avg_time_gap_seconds": round(avg_time_gap_seconds, 1),
            "daily_spend_last_24h": round(daily_spend_last_24h, 2),
            "typical_daily_spending": round(typical_daily_spending, 2)
        }
