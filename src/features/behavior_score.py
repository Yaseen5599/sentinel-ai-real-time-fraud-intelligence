"""
Personalized Behavioral Anomaly Score Calculator
Aggregates behavioral factors into a normalized behavior score [0.0, 1.0] with explainable factors.
"""

from typing import Dict, Any, Tuple, List

class BehaviorScorer:
    """
    Computes an understandable behavior anomaly score from the personalized features.
    """

    def calculate(self, features: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Evaluate behavioral risk factors.
        
        Returns:
            Tuple of (normalized_score, list_of_behavioral_reasons)
        """
        reasons = []
        score_components = []

        # 1. Amount deviation: How far current amount exceeds customer avg / normal max
        amount_ratio = float(features.get("amount_ratio", 1.0))
        if amount_ratio > 3.0:
            score_components.append(0.35)
            reasons.append(f"Amount deviation: Amount is {amount_ratio:.1f}x the customer's average spending.")
        elif amount_ratio > 1.8:
            score_components.append(0.18)
            reasons.append(f"Amount deviation: Amount is {amount_ratio:.1f}x typical baseline.")

        # 2. Transaction velocity (txns in last 5 minutes)
        txns_5m = int(features.get("txns_last_5min", 1))
        if txns_5m > 5:
            score_components.append(0.30)
            reasons.append(f"High velocity: {txns_5m} transactions attempted in the last 5 minutes.")
        elif txns_5m > 3:
            score_components.append(0.15)
            reasons.append(f"Elevated velocity: {txns_5m} transactions in the last 5 minutes.")

        # 3. Geographic diversity
        dist_locs = int(features.get("distinct_locations_last_1h", 1))
        if dist_locs >= 2:
            score_components.append(0.20)
            reasons.append(f"Geographic diversity: Transactions observed in {dist_locs} distinct locations within 1 hour.")

        # 4. Unusual merchant
        if features.get("is_unusual_merchant", False):
            score_components.append(0.10)
            reasons.append("Unusual merchant: Cardholder has never or rarely visited this merchant.")

        # 5. Unusual location
        if features.get("is_unusual_location", False):
            score_components.append(0.12)
            reasons.append("Unusual location: Transaction origin differs from customary transaction locations.")

        # 6. Unusual timing
        if features.get("is_unusual_hour", False):
            score_components.append(0.08)
            reasons.append("Unusual timing: Transaction initiated outside the cardholder's usual operating hours.")

        # 7. Daily spending deviation
        daily_spend = float(features.get("daily_spend_last_24h", 0.0))
        typical_daily = float(features.get("typical_daily_spending", 1.0))
        if typical_daily > 0 and daily_spend > 2.5 * typical_daily:
            ratio = daily_spend / typical_daily
            score_components.append(0.15)
            reasons.append(f"Daily surge: 24h spending (${daily_spend:.2f}) is {ratio:.1f}x normal daily average.")

        # Sum components capped at 1.0
        raw_score = sum(score_components)
        final_score = round(min(1.0, raw_score), 4)

        return final_score, reasons
