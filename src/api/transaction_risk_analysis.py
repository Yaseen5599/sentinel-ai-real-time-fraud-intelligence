"""
Sentinel AI — Transaction Risk Analysis Service
Implements server-side high-performance indexed lookup and hybrid scoring integration
for the 10,000 synthetic transaction dataset and cardholder baselines.
"""

import csv
import math
import time
import pickle
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from config.config import (
    PROJECT_ROOT,
    CANONICAL_MODEL_PATH,
    CANONICAL_SCALER_PATH,
    MODELS_DIR,
    WEIGHT_ML,
    WEIGHT_BEHAVIOR,
    WEIGHT_RULE,
    THRESHOLD_SUSPICIOUS,
    THRESHOLD_FRAUD
)
from src.features.canonical_features import CanonicalFeatureExtractor, CANONICAL_FEATURE_NAMES, haversine_distance_km
from src.features.behavior_score import BehaviorScorer
from src.rules.fraud_rules import FraudRuleEngine, are_locations_distant
from src.models.hybrid_scorer import HybridFraudScorer

DATA_DIR = PROJECT_ROOT / "data" / "real_data"
TRANSACTIONS_CSV_PATH = DATA_DIR / "transactions_10000.csv"
CARDHOLDERS_CSV_PATH = DATA_DIR / "cardholders.csv"


class TransactionRiskAnalysisService:
    """
    Singleton service managing in-memory indices of transactions and cardholders,
    and executing the canonical hybrid fraud scoring pipeline with deep explainability.
    """
    _instance: Optional["TransactionRiskAnalysisService"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.transactions_by_id: Dict[str, Dict[str, Any]] = {}
        self.cardholders_by_id: Dict[str, Dict[str, Any]] = {}
        self.card_history_index: Dict[str, List[Dict[str, Any]]] = {}
        self.is_loaded = False
        self.load_error: Optional[str] = None

        # ML artifacts
        self.rf_model = None
        self.scaler = None
        self.feature_extractor = CanonicalFeatureExtractor()
        self.behavior_scorer = BehaviorScorer()
        self.rule_engine = FraudRuleEngine()
        self.hybrid_scorer = HybridFraudScorer(
            weight_ml=WEIGHT_ML,
            weight_behavior=WEIGHT_BEHAVIOR,
            weight_rule=WEIGHT_RULE,
            suspicious_threshold=THRESHOLD_SUSPICIOUS,
            fraud_threshold=THRESHOLD_FRAUD
        )

        self._load_models()
        self._load_datasets()

    @classmethod
    def get_instance(cls) -> "TransactionRiskAnalysisService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_models(self):
        """Loads canonical Random Forest model and scaler if present."""
        try:
            if CANONICAL_MODEL_PATH.exists() and CANONICAL_SCALER_PATH.exists():
                with open(CANONICAL_MODEL_PATH, "rb") as f:
                    self.rf_model = pickle.load(f)
                with open(CANONICAL_SCALER_PATH, "rb") as f:
                    self.scaler = pickle.load(f)
        except Exception as e:
            self.load_error = f"Failed to load ML artifacts: {str(e)}"

    def _load_datasets(self):
        """Loads and indexes transactions and cardholders into memory."""
        try:
            if not CARDHOLDERS_CSV_PATH.exists() or not TRANSACTIONS_CSV_PATH.exists():
                self.is_loaded = False
                return

            # 1. Load cardholders
            with open(CARDHOLDERS_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cid = row["card_id"].strip()
                    # Parse active hours (e.g. '07:00-22:00')
                    active_hrs = list(range(7, 23))
                    raw_hrs = row.get("usual_active_hours", "")
                    if "-" in raw_hrs:
                        try:
                            start_str, end_str = raw_hrs.split("-")
                            s_hr = int(start_str.split(":")[0])
                            e_hr = int(end_str.split(":")[0])
                            active_hrs = list(range(s_hr, e_hr + 1))
                        except Exception:
                            pass

                    self.cardholders_by_id[cid] = {
                        "card_id": cid,
                        "customer_id": row.get("customer_id", f"CUST_{cid[-3:]}"),
                        "customer_name": row.get("customer_name", f"Customer {cid[-3:]}"),
                        "account_age_days": int(row.get("account_age_days", 365)),
                        "usual_transaction_amount": float(row.get("usual_transaction_amount", 75.0)),
                        "usual_transaction_frequency": float(row.get("usual_transaction_frequency", 2.5)),
                        "usual_active_hours": raw_hrs,
                        "_active_hours_list": active_hrs,
                        "home_location": row.get("home_location", "New York"),
                        "created_at": row.get("created_at", "")
                    }

            # 2. Load transactions
            with open(TRANSACTIONS_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tid = row["transaction_id"].strip().upper()
                    t_record = {
                        "transaction_id": tid,
                        "card_id": row["card_id"].strip(),
                        "amount": float(row["amount"]),
                        "merchant": row["merchant"].strip(),
                        "merchant_name": row["merchant"].strip(),
                        "location": row["location"].strip(),
                        "city": row["location"].strip(),
                        "timestamp": row["timestamp"].strip()
                    }
                    self.transactions_by_id[tid] = t_record

                    # Build per-card history index
                    cid = t_record["card_id"]
                    if cid not in self.card_history_index:
                        self.card_history_index[cid] = []
                    self.card_history_index[cid].append(t_record)

            # Sort per-card history strictly chronologically
            for cid in self.card_history_index:
                self.card_history_index[cid].sort(key=lambda x: x["timestamp"])

            self.is_loaded = True
        except Exception as e:
            self.is_loaded = False
            self.load_error = f"Dataset loading error: {str(e)}"

    def analyze_transaction(self, raw_tx_id: str) -> Dict[str, Any]:
        """
        Executes end-to-end lookup and scoring for the requested transaction ID.
        """
        start_time = time.perf_counter()

        if not self.is_loaded:
            # Try reloading once in case file was just generated
            self._load_datasets()
            if not self.is_loaded:
                raise RuntimeError(self.load_error or "Transaction dataset is currently unavailable on server.")

        tx_id = raw_tx_id.strip().upper()
        if not tx_id.startswith("T"):
            # Normalize e.g. '1' -> 'T00001' or '00001' -> 'T00001'
            if tx_id.isdigit():
                tx_id = f"T{int(tx_id):05d}"

        txn = self.transactions_by_id.get(tx_id)
        if not txn:
            return {"found": False, "transaction_id": tx_id, "error": f"Transaction '{tx_id}' not found in 10,000 dataset."}

        card_id = txn["card_id"]
        cardholder = self.cardholders_by_id.get(card_id)
        if not cardholder:
            return {"found": False, "transaction_id": tx_id, "error": f"Cardholder record for '{card_id}' not found."}

        # Retrieve prior transaction history for this card (strictly prior to current timestamp)
        current_ts = txn["timestamp"]
        card_all = self.card_history_index.get(card_id, [])
        past_txns = [t for t in card_all if t["timestamp"] < current_ts]
        card_history_count = len(past_txns)

        # ----------------------------------------------------------------------
        # 1. Canonical Feature Extraction (Zero Future Data Leakage)
        # ----------------------------------------------------------------------
        baseline_stats = {
            "baseline_avg_amount": cardholder["usual_transaction_amount"],
            "baseline_std_amount": max(10.0, cardholder["usual_transaction_amount"] * 0.45)
        }
        features = self.feature_extractor.extract_features(
            txn=txn,
            card_history=past_txns,
            card_baseline=baseline_stats
        )

        # ----------------------------------------------------------------------
        # 2. Machine Learning Score (Canonical Random Forest)
        # ----------------------------------------------------------------------
        ml_available = (self.rf_model is not None and self.scaler is not None)
        ml_score = 0.0
        ml_explanation = ""
        top_contributing_features = []

        if ml_available:
            try:
                feature_vec = self.feature_extractor.to_feature_vector(features).reshape(1, -1)
                feature_vec_scaled = self.scaler.transform(feature_vec)
                prob = self.rf_model.predict_proba(feature_vec_scaled)[0, 1]
                ml_score = round(float(prob), 4)

                # Identify top input signals based on model importances
                if hasattr(self.rf_model, "feature_importances_"):
                    feat_imps = self.rf_model.feature_importances_
                    scored_feats = []
                    for idx, name in enumerate(CANONICAL_FEATURE_NAMES):
                        val = features.get(name, 0.0)
                        imp = float(feat_imps[idx])
                        scored_feats.append({"feature": name, "value": val, "importance": imp})
                    scored_feats.sort(key=lambda x: x["importance"], reverse=True)
                    top_contributing_features = scored_feats[:5]

                if ml_score >= 0.70:
                    ml_explanation = f"Model predicts high fraud likelihood ({ml_score * 100:.1f}%), heavily influenced by transaction velocity and risk-weighted merchant indicators."
                elif ml_score >= 0.40:
                    ml_explanation = f"Model indicates moderate suspicion ({ml_score * 100:.1f}%) due to mild deviations from typical baseline patterns."
                else:
                    ml_explanation = f"Model evaluates transaction as consistent with legitimate historical spending patterns ({ml_score * 100:.1f}% risk score)."
            except Exception as e:
                ml_available = False
                ml_explanation = f"ML inference failed: {str(e)}"
        else:
            ml_explanation = "Production Canonical Random Forest model is not initialized or artifact is missing."

        # ----------------------------------------------------------------------
        # 3. Customer Behaviour Score & Factor Breakdown
        # ----------------------------------------------------------------------
        cur_amt = txn["amount"]
        usual_amt = cardholder["usual_transaction_amount"]
        amt_ratio = cur_amt / max(1.0, usual_amt)

        # Time analysis
        try:
            txn_dt = datetime.fromisoformat(txn["timestamp"])
            txn_hour = txn_dt.hour
        except Exception:
            txn_hour = 12

        usual_hours_list = cardholder["_active_hours_list"]
        is_unusual_time = txn_hour not in usual_hours_list

        # Velocity in past 5m, 1m, 24h
        velocity_5m = int(features.get("velocity_5m", 0))
        velocity_1m = int(features.get("velocity_1m", 0))
        velocity_24h = int(features.get("velocity_24h", 0))
        spend_24h = float(features.get("spend_velocity_24h", 0.0))

        # Location check
        home_loc = cardholder["home_location"]
        txn_loc = txn["location"]
        past_locs = {t["location"] for t in past_txns}
        is_unusual_location = (txn_loc != home_loc) and (txn_loc not in past_locs) if past_txns else (txn_loc != home_loc)

        # Merchant check
        past_merchants = {t["merchant"] for t in past_txns}
        is_unusual_merchant = (txn["merchant"] not in past_merchants) if past_txns else False

        # Build behavioral feature payload for behavior scorer
        beh_dict = {
            "amount_ratio": amt_ratio,
            "txns_last_5min": velocity_5m + 1,  # include current
            "distinct_locations_last_1h": 2 if features.get("distance_from_last_km", 0) > 300 else 1,
            "is_unusual_merchant": is_unusual_merchant,
            "is_unusual_location": is_unusual_location,
            "is_unusual_hour": is_unusual_time,
            "daily_spend_last_24h": spend_24h + cur_amt,
            "typical_daily_spending": usual_amt * cardholder["usual_transaction_frequency"]
        }
        behavior_score, behavior_reasons = self.behavior_scorer.calculate(beh_dict)

        # Detailed itemized behavioral factor breakdown for examiner UI
        behavior_breakdown = [
            {
                "feature": "Amount Deviation",
                "observed": f"${cur_amt:.2f}",
                "baseline": f"${usual_amt:.2f} avg",
                "condition": f"Ratio {amt_ratio:.2f}x (Threshold > 1.8x / > 3.0x)",
                "weight": 0.35 if amt_ratio > 3.0 else (0.18 if amt_ratio > 1.8 else 0.0),
                "contribution": 0.35 if amt_ratio > 3.0 else (0.18 if amt_ratio > 1.8 else 0.0),
                "status": "ELEVATED" if amt_ratio > 1.8 else "NORMAL",
                "impact": "High spending deviation" if amt_ratio > 3.0 else ("Moderate deviation" if amt_ratio > 1.8 else "Within baseline")
            },
            {
                "feature": "Transaction Velocity (5m)",
                "observed": f"{velocity_5m + 1} txns",
                "baseline": "Normal < 3 txns",
                "condition": f"{velocity_5m + 1} attempts in 5-minute window",
                "weight": 0.30 if (velocity_5m + 1) > 5 else (0.15 if (velocity_5m + 1) > 3 else 0.0),
                "contribution": 0.30 if (velocity_5m + 1) > 5 else (0.15 if (velocity_5m + 1) > 3 else 0.0),
                "status": "ELEVATED" if (velocity_5m + 1) > 3 else "NORMAL",
                "impact": "Velocity burst detected" if (velocity_5m + 1) > 3 else "Normal rate"
            },
            {
                "feature": "Diurnal Active Hours",
                "observed": f"{txn_hour:02d}:00 UTC",
                "baseline": cardholder["usual_active_hours"],
                "condition": "Initiated outside usual operating hours",
                "weight": 0.08 if is_unusual_time else 0.0,
                "contribution": 0.08 if is_unusual_time else 0.0,
                "status": "ELEVATED" if is_unusual_time else "NORMAL",
                "impact": "Unusual night/early morning spending" if is_unusual_time else "Within typical active hours"
            },
            {
                "feature": "Location Familiarity",
                "observed": txn_loc,
                "baseline": f"Home: {home_loc}",
                "condition": "Transaction terminal differs from primary & customary locations",
                "weight": 0.12 if is_unusual_location else 0.0,
                "contribution": 0.12 if is_unusual_location else 0.0,
                "status": "ELEVATED" if is_unusual_location else "NORMAL",
                "impact": "Terminal in unfamiliar geographic location" if is_unusual_location else "Customary location"
            },
            {
                "feature": "Merchant Familiarity",
                "observed": txn["merchant"],
                "baseline": f"{len(past_merchants)} previously visited merchants",
                "condition": "Cardholder has never transacted at this merchant",
                "weight": 0.10 if is_unusual_merchant else 0.0,
                "contribution": 0.10 if is_unusual_merchant else 0.0,
                "status": "ELEVATED" if is_unusual_merchant else "NORMAL",
                "impact": "First-time merchant interaction" if is_unusual_merchant else "Known merchant"
            }
        ]

        # ----------------------------------------------------------------------
        # 4. Rule Score & Rule Engine Evaluation
        # ----------------------------------------------------------------------
        txn_for_rules = {
            "amount": cur_amt,
            "timestamp": txn["timestamp"],
            "card_id": card_id,
            "merchant": txn["merchant"],
            "location": txn["location"],
            "avg_amount": usual_amt,
            "usual_hours": usual_hours_list,
            "frequent_merchants": list(past_merchants),
            "status": "SUCCESS"
        }

        rule_score, triggered_rule_keys, rule_reasons = self.rule_engine.evaluate(
            txn=txn_for_rules,
            card_history=past_txns
        )

        all_rules_catalog = [
            {
                "rule_id": "RULE_1_BURST_TXNS",
                "name": "Rapid Burst Transactions",
                "condition": "> 5 transactions within 2 minutes",
                "threshold": "5 txns / 2 min",
                "observed": f"{features.get('velocity_1m', 0):.0f} txns in recent window",
                "weight": self.rule_engine.rule_weights["RULE_1_BURST_TXNS"]
            },
            {
                "rule_id": "RULE_2_IMPOSSIBLE_TRAVEL",
                "name": "Impossible Travel Velocity",
                "condition": "Distant geographic terminal (>300 km) within 30 minutes",
                "threshold": "> 300 km in 30 min",
                "observed": f"{features.get('distance_from_last_km', 0):.1f} km from prior txn",
                "weight": self.rule_engine.rule_weights["RULE_2_IMPOSSIBLE_TRAVEL"]
            },
            {
                "rule_id": "RULE_3_HIGH_AMOUNT_MULTIPLE",
                "name": "High Amount Spike",
                "condition": "Transaction amount > 3.0x cardholder average",
                "threshold": f"> ${usual_amt * 3.0:.2f}",
                "observed": f"${cur_amt:.2f} ({amt_ratio:.1f}x avg)",
                "weight": self.rule_engine.rule_weights["RULE_3_HIGH_AMOUNT_MULTIPLE"]
            },
            {
                "rule_id": "RULE_4_NEW_MERCHANT_HIGH_AMOUNT",
                "name": "Unfamiliar Merchant High Spend",
                "condition": "New merchant combined with amount > 2.0x average",
                "threshold": f"Unseen merchant & > ${usual_amt * 2.0:.2f}",
                "observed": f"Merchant '{txn['merchant']}', ${cur_amt:.2f}",
                "weight": self.rule_engine.rule_weights["RULE_4_NEW_MERCHANT_HIGH_AMOUNT"]
            },
            {
                "rule_id": "RULE_5_DECLINED_FOLLOWED_BY_SUCCESS",
                "name": "Card Testing Pattern",
                "condition": ">= 2 declined attempts followed by success",
                "threshold": "2 declines prior to success",
                "observed": "No prior declined sequence recorded",
                "weight": self.rule_engine.rule_weights["RULE_5_DECLINED_FOLLOWED_BY_SUCCESS"]
            },
            {
                "rule_id": "RULE_6_MERCHANT_CARD_SWARM",
                "name": "Merchant Card Swarm",
                "condition": ">= 4 distinct cards at same merchant within 5 minutes",
                "threshold": ">= 4 distinct cards / 5 min",
                "observed": "Single card interaction",
                "weight": self.rule_engine.rule_weights["RULE_6_MERCHANT_CARD_SWARM"]
            },
            {
                "rule_id": "RULE_7_UNUSUAL_TIME",
                "name": "Unusual Time Transaction",
                "condition": "Transaction initiated outside normal active hours",
                "threshold": cardholder["usual_active_hours"],
                "observed": f"{txn_hour:02d}:00 UTC",
                "weight": self.rule_engine.rule_weights["RULE_7_UNUSUAL_TIME"]
            }
        ]

        rules_evaluated_breakdown = []
        for r_meta in all_rules_catalog:
            r_id = r_meta["rule_id"]
            is_trig = (r_id in triggered_rule_keys)
            rules_evaluated_breakdown.append({
                "rule_id": r_id,
                "name": r_meta["name"],
                "condition": r_meta["condition"],
                "threshold": r_meta["threshold"],
                "observed": r_meta["observed"],
                "weight": r_meta["weight"],
                "triggered": is_trig,
                "contribution": r_meta["weight"] if is_trig else 0.0
            })

        # ----------------------------------------------------------------------
        # 5. Final Hybrid Risk Score Arithmetic
        # ----------------------------------------------------------------------
        effective_ml_score = ml_score if ml_available else 0.0
        final_risk_score = round(
            (WEIGHT_ML * effective_ml_score) +
            (WEIGHT_BEHAVIOR * behavior_score) +
            (WEIGHT_RULE * rule_score),
            4
        )
        final_risk_score = min(1.0, max(0.0, final_risk_score))

        if final_risk_score >= THRESHOLD_FRAUD:
            classification = "HIGH_RISK"
            classification_display = "High Risk / Fraud Alert"
            color_badge = "rose"
        elif final_risk_score >= THRESHOLD_SUSPICIOUS:
            classification = "SUSPICIOUS"
            classification_display = "Suspicious / Medium Risk"
            color_badge = "amber"
        else:
            classification = "LEGITIMATE"
            classification_display = "Legitimate / Low Risk"
            color_badge = "emerald"

        arithmetic_formula = (
            f"({WEIGHT_ML:.2f} × {effective_ml_score:.2f} [ML]) + "
            f"({WEIGHT_BEHAVIOR:.2f} × {behavior_score:.2f} [Behaviour]) + "
            f"({WEIGHT_RULE:.2f} × {rule_score:.2f} [Rule]) = {final_risk_score:.4f}"
        )

        # ----------------------------------------------------------------------
        # 6. Plain-English Grounded Audit Explanation
        # ----------------------------------------------------------------------
        explanation_sentences = []

        if classification == "HIGH_RISK":
            explanation_sentences.append(
                f"Transaction {tx_id} was classified as High Risk (score: {final_risk_score:.2f}) "
                f"surpassing the critical fraud threshold ({THRESHOLD_FRAUD:.2f})."
            )
        elif classification == "SUSPICIOUS":
            explanation_sentences.append(
                f"Transaction {tx_id} was classified as Suspicious (score: {final_risk_score:.2f}) "
                f"falling within the configured medium-risk monitoring band ({THRESHOLD_SUSPICIOUS:.2f} – {THRESHOLD_FRAUD:.2f})."
            )
        else:
            explanation_sentences.append(
                f"Transaction {tx_id} was classified as Legitimate (score: {final_risk_score:.2f}) "
                f"remaining well below the suspicious review threshold ({THRESHOLD_SUSPICIOUS:.2f})."
            )

        # Concrete evidence reasons
        evidence_points = []
        if triggered_rule_keys:
            trig_names = [r["name"] for r in rules_evaluated_breakdown if r["triggered"]]
            evidence_points.append(f"{len(triggered_rule_keys)} deterministic rule(s) triggered ({', '.join(trig_names)})")

        if amt_ratio > 3.0:
            evidence_points.append(f"spending amount (${cur_amt:.2f}) is {amt_ratio:.1f}x the cardholder's historical average (${usual_amt:.2f})")
        elif amt_ratio > 1.8:
            evidence_points.append(f"amount (${cur_amt:.2f}) is noticeably elevated above typical spend (${usual_amt:.2f})")

        if velocity_5m > 3:
            evidence_points.append(f"high transaction frequency with {velocity_5m + 1} transactions attempted in 5 minutes")

        if is_unusual_time:
            evidence_points.append(f"activity occurred at {txn_hour:02d}:00 UTC outside normal active hours ({cardholder['usual_active_hours']})")

        if is_unusual_location:
            evidence_points.append(f"terminal location '{txn_loc}' deviates from home base '{home_loc}'")

        if ml_available:
            if ml_score >= 0.70:
                evidence_points.append(f"the supervised Random Forest model returned an elevated risk probability of {ml_score * 100:.1f}%")
            elif ml_score <= 0.20:
                evidence_points.append(f"the supervised model verified canonical spending patterns with low probability ({ml_score * 100:.1f}%)")

        if evidence_points:
            explanation_sentences.append("Key contributing factors include: " + "; ".join(evidence_points) + ".")
        else:
            explanation_sentences.append("All behavioral factors, rule evaluations, and machine learning inferences align with customary cardholder activity.")

        explanation_sentences.append(
            "Note: This score is a real-time statistical risk assessment and fraud alert indicator, "
            "not a confirmed chargeback or final fraud legal outcome."
        )

        plain_english_audit = " ".join(explanation_sentences)

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Mask card ID for PCI compliance
        card_id_masked = f"CARD_***_{card_id[-3:]}" if len(card_id) >= 3 else "CARD_***"

        return {
            "found": True,
            "transaction_id": tx_id,
            "timestamp": txn["timestamp"],
            "amount": cur_amt,
            "currency": "USD",
            "merchant": txn["merchant"],
            "location": txn["location"],
            "card_id": card_id,
            "card_id_masked": card_id_masked,
            "data_source": "Synthetic Benchmark Dataset (transactions_10000.csv / cardholders.csv)",
            "is_synthetic": True,
            "customer": {
                "customer_id": cardholder["customer_id"],
                "customer_name": cardholder["customer_name"],
                "account_age_days": cardholder["account_age_days"],
                "home_location": cardholder["home_location"],
                "usual_transaction_amount": cardholder["usual_transaction_amount"],
                "usual_active_hours": cardholder["usual_active_hours"],
                "prior_transaction_count": card_history_count
            },
            "scores": {
                "ml_score": ml_score,
                "ml_available": ml_available,
                "behavior_score": behavior_score,
                "rule_score": rule_score,
                "final_risk_score": final_risk_score,
                "classification": classification,
                "classification_display": classification_display,
                "color_badge": color_badge,
                "weights": {
                    "ml_weight": WEIGHT_ML,
                    "behavior_weight": WEIGHT_BEHAVIOR,
                    "rule_weight": WEIGHT_RULE
                },
                "thresholds": {
                    "suspicious": THRESHOLD_SUSPICIOUS,
                    "fraud": THRESHOLD_FRAUD
                },
                "arithmetic_formula": arithmetic_formula
            },
            "explanations": {
                "plain_english_audit": plain_english_audit,
                "ml": {
                    "model_name": "Canonical Random Forest (Zero Train-Serve Skew)",
                    "model_version": "canonical-rf-v1.0",
                    "available": ml_available,
                    "score": ml_score,
                    "decision_threshold": 0.50,
                    "explanation": ml_explanation,
                    "input_features": features,
                    "top_contributing_features": top_contributing_features,
                    "limitations": "Model trained on synthetic canonical benchmarks. Real-world generalization requires bank-specific production calibration."
                },
                "behavior": {
                    "score": behavior_score,
                    "reasons": behavior_reasons,
                    "breakdown": behavior_breakdown
                },
                "rules": {
                    "score": rule_score,
                    "triggered_count": len(triggered_rule_keys),
                    "total_evaluated": len(all_rules_catalog),
                    "reasons": rule_reasons,
                    "rules": rules_evaluated_breakdown
                },
                "hybrid": {
                    "final_score": final_risk_score,
                    "formula": arithmetic_formula,
                    "classification": classification_display,
                    "rule_weight": WEIGHT_RULE,
                    "behavior_weight": WEIGHT_BEHAVIOR,
                    "ml_weight": WEIGHT_ML,
                    "suspicious_threshold": THRESHOLD_SUSPICIOUS,
                    "fraud_threshold": THRESHOLD_FRAUD
                }
            },
            "telemetry": {
                "processing_latency_ms": latency_ms,
                "evaluated_at": datetime.now(timezone.utc).isoformat()
            }
        }
