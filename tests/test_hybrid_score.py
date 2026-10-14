"""
Unit tests for Hybrid Risk Scorer
"""

import pytest
from src.models.hybrid_scorer import HybridFraudScorer

def test_fixed_weights():
    """Verify that score obeys exact formula: 0.5*ML + 0.3*Behavior + 0.2*Rule."""
    scorer = HybridFraudScorer()

    ml_s = 0.80
    beh_s = 0.60
    rule_s = 0.50

    expected = (0.5 * ml_s) + (0.3 * beh_s) + (0.2 * rule_s)
    # 0.40 + 0.18 + 0.10 = 0.68

    result = scorer.calculate_score(ml_s, beh_s, rule_s)
    assert result["final_fraud_score"] == pytest.approx(expected, 0.001)
    assert result["fraud_decision"] == "SUSPICIOUS"  # 0.68 is >= 0.45 and < 0.70

def test_fraud_classification():
    scorer = HybridFraudScorer()
    # High score >= 0.70
    result = scorer.calculate_score(0.9, 0.8, 0.8)
    # 0.45 + 0.24 + 0.16 = 0.85
    assert result["final_fraud_score"] == pytest.approx(0.85, 0.001)
    assert result["fraud_decision"] == "FRAUD"

def test_legitimate_classification():
    scorer = HybridFraudScorer()
    # Low score < 0.45
    result = scorer.calculate_score(0.1, 0.1, 0.0)
    assert result["final_fraud_score"] < 0.45
    assert result["fraud_decision"] == "LEGITIMATE"
