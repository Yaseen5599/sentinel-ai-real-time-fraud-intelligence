"""
Hybrid Fraud Risk Scorer
Combines:
  1. Supervised Machine Learning Score (weight = 0.5)
  2. Personalized Behavioral Anomaly Score (weight = 0.3)
  3. Deterministic Rule Engine Score (weight = 0.2)

Strict Formula:
  Fraud Score = 0.5 * ML Score + 0.3 * Behavior Score + 0.2 * Rule Score
"""

from typing import Dict, Any, List, Tuple
from config.config import (
    WEIGHT_ML,
    WEIGHT_BEHAVIOR,
    WEIGHT_RULE,
    THRESHOLD_SUSPICIOUS,
    THRESHOLD_FRAUD
)

class HybridFraudScorer:
    """
    Computes weighted hybrid fraud risk score and determines final alert classification
    with human-readable explainability.
    """

    def __init__(self,
                 weight_ml: float = WEIGHT_ML,
                 weight_behavior: float = WEIGHT_BEHAVIOR,
                 weight_rule: float = WEIGHT_RULE,
                 suspicious_threshold: float = THRESHOLD_SUSPICIOUS,
                 fraud_threshold: float = THRESHOLD_FRAUD):
        self.w_ml = weight_ml
        self.w_behavior = weight_behavior
        self.w_rule = weight_rule
        self.suspicious_threshold = suspicious_threshold
        self.fraud_threshold = fraud_threshold

    def calculate_score(self,
                        ml_score: float,
                        behavior_score: float,
                        rule_score: float,
                        rule_explanations: List[str] = None,
                        behavior_explanations: List[str] = None) -> Dict[str, Any]:
        """
        Calculates final hybrid fraud score, decision, and consolidated explanation.
        """
        # Ensure inputs are normalized [0.0, 1.0]
        ml_s = max(0.0, min(1.0, float(ml_score)))
        beh_s = max(0.0, min(1.0, float(behavior_score)))
        rule_s = max(0.0, min(1.0, float(rule_score)))

        # Weighted combination
        final_score = (self.w_ml * ml_s) + (self.w_behavior * beh_s) + (self.w_rule * rule_s)
        final_score = round(min(1.0, max(0.0, final_score)), 4)

        # Decision
        if final_score >= self.fraud_threshold:
            decision = "FRAUD"
        elif final_score >= self.suspicious_threshold:
            decision = "SUSPICIOUS"
        else:
            decision = "LEGITIMATE"

        # Consolidate human-readable explanations
        reasons = []
        if rule_explanations:
            reasons.extend(rule_explanations)
        if behavior_explanations:
            reasons.extend(behavior_explanations)

        if ml_s >= 0.5:
            reasons.append(f"ML Classifier high fraud probability: {ml_s * 100:.1f}%.")

        if not reasons:
            if decision == "LEGITIMATE":
                explanation_str = "Transaction patterns consistent with normal customer spending."
            else:
                explanation_str = f"Elevated cumulative risk score ({final_score:.2f}) across behavioral & ML indicators."
        else:
            explanation_str = " | ".join(reasons)

        return {
            "ml_score": ml_s,
            "behavior_score": beh_s,
            "rule_score": rule_s,
            "final_fraud_score": final_score,
            "fraud_decision": decision,
            "explanation": explanation_str,
            "reasons_list": reasons
        }
