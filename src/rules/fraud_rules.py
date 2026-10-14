"""
Fraud Rule Engine
Implements the 7 explicit fraud detection rules required by the project specification.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

from src.features.canonical_features import haversine_distance_km

# Estimated city coordinates lookup for precision distance checking
CITY_COORDINATES = {
    "New York": (40.7128, -74.0060),
    "London": (51.5074, -0.1278),
    "Tokyo": (35.6762, 139.6503),
    "Singapore": (1.3521, 103.8198),
    "San Francisco": (37.7749, -122.4194),
    "Paris": (48.8566, 2.3522),
    "Chicago": (41.8781, -87.6298),
    "Seattle": (47.6062, -122.3321),
    "Boston": (42.3601, -71.0589),
    "Sydney": (-33.8688, 151.2093),
    "Mumbai": (19.0760, 72.8777),
}

def are_locations_distant(loc1: str, loc2: str, lat1: float = None, lon1: float = None, lat2: float = None, lon2: float = None) -> bool:
    if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
        return haversine_distance_km(lat1, lon1, lat2, lon2) > 300.0  # >300 km is distant
    
    if loc1 in CITY_COORDINATES and loc2 in CITY_COORDINATES:
        c1, c2 = CITY_COORDINATES[loc1], CITY_COORDINATES[loc2]
        return haversine_distance_km(c1[0], c1[1], c2[0], c2[1]) > 300.0

    if not loc1 or not loc2 or loc1 == loc2:
        return False
    return True

class FraudRuleEngine:
    """
    Evaluates transactions against the 7 defined rules and outputs
    a normalized rule score [0.0, 1.0] along with explainable reasons.
    """

    def __init__(self):
        # Rule severity weights (summing to 1.0 for normalized scoring)
        self.rule_weights = {
            "RULE_1_BURST_TXNS": 0.20,
            "RULE_2_IMPOSSIBLE_TRAVEL": 0.25,
            "RULE_3_HIGH_AMOUNT_MULTIPLE": 0.15,
            "RULE_4_NEW_MERCHANT_HIGH_AMOUNT": 0.15,
            "RULE_5_DECLINED_FOLLOWED_BY_SUCCESS": 0.10,
            "RULE_6_MERCHANT_CARD_SWARM": 0.05,
            "RULE_7_UNUSUAL_TIME": 0.10,
        }

    def evaluate(self, txn: Dict[str, Any], card_history: List[Dict[str, Any]], merchant_history: List[Dict[str, Any]] = None) -> Tuple[float, List[str], List[str]]:
        """
        Evaluate a transaction against all 7 rules.
        
        Args:
            txn: Current transaction dict with fields:
                 amount, timestamp, card_id, merchant, location, avg_amount, usual_hours, frequent_merchants, status, etc.
            card_history: List of recent transactions for this cardholder (strictly prior to or including current).
            merchant_history: Optional recent transactions at this merchant from all cards.

        Returns:
            Tuple of (normalized_score, triggered_rules, explanations)
        """
        triggered_rules = []
        explanations = []

        txn_time = txn.get("timestamp")
        if isinstance(txn_time, str):
            txn_time = datetime.fromisoformat(txn_time)

        amount = float(txn.get("amount", 0.0))
        card_id = txn.get("card_id", "")
        merchant = txn.get("merchant", "")
        location = txn.get("location", "")
        avg_amount = float(txn.get("avg_amount", 100.0))
        usual_hours = txn.get("usual_hours", list(range(7, 23)))  # default 7am - 11pm
        frequent_merchants = txn.get("frequent_merchants", [])
        status = txn.get("status", "SUCCESS")

        # ------------------------------------------------------------------
        # Rule 1: More than five transactions from one card within two minutes
        # ------------------------------------------------------------------
        two_mins_ago = txn_time - timedelta(minutes=2)
        recent_2m_txns = [
            t for t in card_history 
            if (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]) >= two_mins_ago
        ]
        if len(recent_2m_txns) > 5:
            triggered_rules.append("RULE_1_BURST_TXNS")
            explanations.append(f"Rapid velocity detected: {len(recent_2m_txns)} transactions occurred from this card within 2 minutes.")

        # ------------------------------------------------------------------
        # Rule 2: Two transactions from geographically distant locations within a short period
        # ------------------------------------------------------------------
        thirty_mins_ago = txn_time - timedelta(minutes=30)
        recent_distant = [
            t for t in card_history
            if (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]) >= thirty_mins_ago
            and t.get("location") != location and are_locations_distant(t.get("location", ""), location)
        ]
        if recent_distant:
            prior_loc = recent_distant[-1].get("location")
            triggered_rules.append("RULE_2_IMPOSSIBLE_TRAVEL")
            explanations.append(f"Impossible travel alert: Transaction in '{location}' occurred within 30 minutes of a transaction in '{prior_loc}'.")

        # ------------------------------------------------------------------
        # Rule 3: Transaction amount is more than three times the customer's normal average
        # ------------------------------------------------------------------
        if avg_amount > 0 and amount > 3.0 * avg_amount:
            ratio = amount / avg_amount
            triggered_rules.append("RULE_3_HIGH_AMOUNT_MULTIPLE")
            explanations.append(f"Amount spike: Transaction amount (${amount:.2f}) is {ratio:.1f}x the customer's historical average (${avg_amount:.2f}).")

        # ------------------------------------------------------------------
        # Rule 4: New merchant combined with an unusually high amount
        # ------------------------------------------------------------------
        is_new_merchant = bool(frequent_merchants and merchant not in frequent_merchants)
        if is_new_merchant and amount > 2.0 * avg_amount:
            triggered_rules.append("RULE_4_NEW_MERCHANT_HIGH_AMOUNT")
            explanations.append(f"Unfamiliar merchant high spend: Unseen merchant '{merchant}' with elevated amount (${amount:.2f}).")

        # ------------------------------------------------------------------
        # Rule 5: Several declined transactions followed by a successful high-value transaction
        # ------------------------------------------------------------------
        ten_mins_ago = txn_time - timedelta(minutes=10)
        declined_txns = [
            t for t in card_history
            if (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]) >= ten_mins_ago
            and t.get("status") == "DECLINED"
        ]
        if len(declined_txns) >= 2 and status == "SUCCESS" and amount >= avg_amount:
            triggered_rules.append("RULE_5_DECLINED_FOLLOWED_BY_SUCCESS")
            explanations.append(f"Card testing pattern: {len(declined_txns)} declined transactions immediately preceded this high-value success.")

        # ------------------------------------------------------------------
        # Rule 6: Multiple cards being used at the same merchant within a short time
        # ------------------------------------------------------------------
        if merchant_history:
            five_mins_ago = txn_time - timedelta(minutes=5)
            recent_merchant_cards = set(
                t.get("card_id") for t in merchant_history
                if (datetime.fromisoformat(t["timestamp"]) if isinstance(t["timestamp"], str) else t["timestamp"]) >= five_mins_ago
            )
            # Add current card
            recent_merchant_cards.add(card_id)
            if len(recent_merchant_cards) >= 4:
                triggered_rules.append("RULE_6_MERCHANT_CARD_SWARM")
                explanations.append(f"Merchant swarm: {len(recent_merchant_cards)} distinct cards used at '{merchant}' within 5 minutes.")

        # ------------------------------------------------------------------
        # Rule 7: Transaction occurring at an unusual time for that customer
        # ------------------------------------------------------------------
        txn_hour = txn_time.hour
        if usual_hours and txn_hour not in usual_hours:
            triggered_rules.append("RULE_7_UNUSUAL_TIME")
            explanations.append(f"Unusual timing: Transaction initiated at {txn_hour:02d}:00, outside customer's regular active hours ({min(usual_hours):02d}:00-{max(usual_hours):02d}:00).")

        # Calculate score (capped at 1.0)
        raw_score = sum(self.rule_weights.get(r, 0.1) for r in triggered_rules)
        score = min(1.0, raw_score)

        return round(score, 4), triggered_rules, explanations
