"""
Sentinel AI — Canonical Model Training Pipeline
Trains production Supervised Classifier (Random Forest) and Unsupervised Anomaly Detector (Isolation Forest)
directly on the 18 canonical features with zero train-serve skew, realistic overlapping noise,
and dual evaluation (strict chronological temporal split AND cardholder-disjoint out-of-distribution split).
"""

import os
import sys
import pickle
import time
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    confusion_matrix
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config import (
    MODELS_DIR,
    CANONICAL_MODEL_PATH,
    CANONICAL_SCALER_PATH,
    CANONICAL_ISOLATION_PATH,
    CANONICAL_TRAINING_DATA_PATH,
    ASSUMED_COST_FN,
    ASSUMED_COST_FP
)
from src.producer.transaction_generator import TransactionGenerator, CARDHOLDERS
from src.features.canonical_features import CanonicalFeatureExtractor, CANONICAL_FEATURE_NAMES

def generate_canonical_dataset(num_normal: int = 12000, fraud_ratio: float = 0.02) -> pd.DataFrame:
    """
    Generates a realistic chronological dataset of canonical transactions
    with historical state preservation and overlapping real-world noise.
    """
    print(f"[Data Prep] Generating {num_normal} canonical transactions across 30 cardholders with realistic noise...")
    gen = TransactionGenerator(seed=42)
    extractor = CanonicalFeatureExtractor()

    start_date = datetime(2026, 8, 1, 8, 0, 0, tzinfo=timezone.utc)
    card_histories = {cid: [] for cid in CARDHOLDERS}

    records = []
    current_time = start_date

    total_events = int(num_normal / (1.0 - fraud_ratio))
    scenario_types = [
        "RAPID_TRANSACTION_BURST",
        "IMPOSSIBLE_TRAVEL",
        "HIGH_VALUE_ABNORMAL_SPIKE",
        "ACCOUNT_TAKEOVER",
        "CARD_TESTING_DECLINED"
    ]

    for i in range(total_events):
        current_time += timedelta(seconds=np.random.exponential(scale=60.0))
        is_fraud = (np.random.random() < fraud_ratio)

        card_id = np.random.choice(list(CARDHOLDERS.keys()))

        if is_fraud:
            scenario = np.random.choice(scenario_types)
            if scenario == "HIGH_VALUE_ABNORMAL_SPIKE":
                txn = gen.generate_scenario_high_value_spike(card_id=card_id)
                txn["timestamp"] = current_time.isoformat()
                txns_to_process = [(txn, 1)]
            elif scenario == "ACCOUNT_TAKEOVER":
                txn = gen.generate_scenario_account_takeover(card_id=card_id)
                txn["timestamp"] = current_time.replace(hour=3).isoformat()
                txns_to_process = [(txn, 1)]
            elif scenario == "IMPOSSIBLE_TRAVEL":
                s_txns = gen.generate_scenario_impossible_travel(card_id=card_id)
                s_txns[0]["timestamp"] = (current_time - timedelta(minutes=15)).isoformat()
                s_txns[1]["timestamp"] = current_time.isoformat()
                txns_to_process = [(s_txns[0], 0), (s_txns[1], 1)]
            elif scenario == "RAPID_TRANSACTION_BURST":
                burst = gen.generate_scenario_rapid_burst(card_id=card_id, count=6)
                txns_to_process = []
                for b_idx, b in enumerate(burst):
                    b["timestamp"] = (current_time + timedelta(seconds=b_idx * 10)).isoformat()
                    txns_to_process.append((b, 1 if b_idx >= 3 else 0))
            else:
                testing = gen.generate_scenario_declined_card_testing(card_id=card_id)
                txns_to_process = []
                for t_idx, t in enumerate(testing):
                    t["timestamp"] = (current_time + timedelta(minutes=t_idx * 2)).isoformat()
                    txns_to_process.append((t, 1))
        else:
            txn = gen.generate_normal_transaction(card_id=card_id, timestamp=current_time)
            # Realistic overlapping behavioral noise for legitimate cardholders:
            # 1. 3% legitimate travel (different city)
            if np.random.random() < 0.03:
                travel_cities = ["New York", "San Francisco", "London", "Miami", "Denver"]
                new_city = np.random.choice(travel_cities)
                txn["city"] = new_city
                txn["location"] = new_city
            # 2. 4% purchase at unfamiliar merchant
            if np.random.random() < 0.04:
                unfamiliar = ["Apex Electronics", "Urban Retail", "Grand Hyatt Hotel", "Boutique Gallery"]
                txn["merchant_name"] = np.random.choice(unfamiliar)
                txn["merchant"] = txn["merchant_name"]
            # 3. 2% occasional high-value normal purchase (appliances/flights)
            if np.random.random() < 0.02:
                txn["amount"] = round(float(np.random.uniform(320.0, 950.0)), 2)
            # 4. 1.5% legitimate entry error / decline
            if np.random.random() < 0.015:
                txn["authorization_status"] = "DECLINED"
                txn["status"] = "DECLINED"

            txns_to_process = [(txn, 0)]

        for item_txn, label in txns_to_process:
            c_id = item_txn["card_id"]
            feats = extractor.extract_features(item_txn, card_history=card_histories[c_id])
            feats["is_fraud"] = label
            feats["transaction_id"] = item_txn["transaction_id"]
            feats["card_id"] = c_id
            feats["timestamp"] = item_txn["timestamp"]
            records.append(feats)

            # Update historical state
            card_histories[c_id].append(item_txn)
            if len(card_histories[c_id]) > 500:
                card_histories[c_id] = card_histories[c_id][-500:]

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    return df

def evaluate_metrics(name: str, y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    pr_auc = average_precision_score(y_true, y_prob) if y_prob is not None else 0.0

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    total = len(y_true)
    fp_per_1000 = (fp / total) * 1000.0
    total_cost = (ASSUMED_COST_FN * fn) + (ASSUMED_COST_FP * fp)

    return {
        "model": name,
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "pr_auc": round(float(pr_auc), 4),
        "fp_per_1000": round(float(fp_per_1000), 2),
        "total_cost": round(float(total_cost), 2),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn)
    }

def run_canonical_training():
    df = generate_canonical_dataset(num_normal=12000, fraud_ratio=0.02)
    print(f" -> Total dataset: {len(df):,} transactions. Fraud cases: {(df['is_fraud']==1).sum():,} ({((df['is_fraud']==1).sum()/len(df)*100):.2f}%)")

    # Save processed training parquet (ensure timestamp is string for PySpark Parquet compatibility)
    CANONICAL_TRAINING_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_export = df.copy()
    df_export["timestamp"] = df_export["timestamp"].astype(str)
    df_export.to_parquet(CANONICAL_TRAINING_DATA_PATH, index=False)
    print(f" -> Saved canonical training dataset to {CANONICAL_TRAINING_DATA_PATH}")

    # --------------------------------------------------------------------------
    # Benchmark 1: Strict Chronological Split (80% Train, 20% Test)
    # --------------------------------------------------------------------------
    split_idx = int(0.80 * len(df))
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    print(f"\n[Split 1: Temporal Chronological] Train = {len(train_df):,} txns | Test = {len(test_df):,} txns")

    X_train = train_df[CANONICAL_FEATURE_NAMES].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[CANONICAL_FEATURE_NAMES].values
    y_test = test_df["is_fraud"].values

    # Fit scaler strictly on training data
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Production Random Forest Classifier
    print("[Training] Fitting Canonical Random Forest Classifier...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(X_train_scaled, y_train)

    rf_prob = rf.predict_proba(X_test_scaled)[:, 1]
    rf_pred = (rf_prob >= 0.50).astype(int)
    rf_metrics = evaluate_metrics("Canonical Random Forest (Temporal)", y_test, rf_pred, rf_prob)

    # Production Isolation Forest (Fitted strictly on normal training transactions)
    print("[Training] Fitting Canonical Isolation Forest...")
    X_train_normal = X_train_scaled[y_train == 0]
    iso = IsolationForest(n_estimators=100, contamination=0.015, random_state=42, n_jobs=-1)
    iso.fit(X_train_normal)

    iso_scores = -iso.score_samples(X_test_scaled)
    iso_prob = (iso_scores - iso_scores.min()) / (iso_scores.max() - iso_scores.min() + 1e-9)
    iso_pred = np.where(iso.predict(X_test_scaled) == -1, 1, 0)
    iso_metrics = evaluate_metrics("Canonical Isolation Forest (Temporal)", y_test, iso_pred, iso_prob)

    # --------------------------------------------------------------------------
    # Benchmark 2: Cardholder-Disjoint Split (Out-of-Distribution Generalization)
    # --------------------------------------------------------------------------
    all_cards = sorted(list(df["card_id"].unique()))
    n_train_cards = int(0.80 * len(all_cards))
    train_cards = set(all_cards[:n_train_cards])
    test_cards = set(all_cards[n_train_cards:])

    df_card_train = df[df["card_id"].isin(train_cards)]
    df_card_test = df[df["card_id"].isin(test_cards)]

    print(f"\n[Split 2: Cardholder Disjoint] Train Cards = {len(train_cards)} ({len(df_card_train):,} txns) | Test Cards = {len(test_cards)} ({len(df_card_test):,} txns)")

    X_ctrain = df_card_train[CANONICAL_FEATURE_NAMES].values
    y_ctrain = df_card_train["is_fraud"].values
    X_ctest = df_card_test[CANONICAL_FEATURE_NAMES].values
    y_ctest = df_card_test["is_fraud"].values

    c_scaler = StandardScaler()
    X_ctrain_scaled = c_scaler.fit_transform(X_ctrain)
    X_ctest_scaled = c_scaler.transform(X_ctest)

    rf_disjoint = RandomForestClassifier(n_estimators=100, max_depth=10, class_weight="balanced", random_state=42, n_jobs=-1)
    rf_disjoint.fit(X_ctrain_scaled, y_ctrain)
    rf_disjoint_prob = rf_disjoint.predict_proba(X_ctest_scaled)[:, 1]
    rf_disjoint_pred = (rf_disjoint_prob >= 0.50).astype(int)
    rf_disjoint_metrics = evaluate_metrics("Canonical RF (Cardholder Disjoint)", y_ctest, rf_disjoint_pred, rf_disjoint_prob)

    print("\n================== CANONICAL DUAL-BENCHMARK RESULTS ==================")
    res_df = pd.DataFrame([rf_metrics, iso_metrics, rf_disjoint_metrics])
    print(res_df[["model", "precision", "recall", "f1_score", "pr_auc", "fp_per_1000", "total_cost"]].to_string(index=False))
    print("======================================================================")

    # Serialize active model artifacts
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CANONICAL_MODEL_PATH, "wb") as f:
        pickle.dump(rf, f)
    with open(CANONICAL_SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    with open(CANONICAL_ISOLATION_PATH, "wb") as f:
        pickle.dump(iso, f)

    # Save model metadata JSON with dual-benchmark metrics
    feature_importances = {
        CANONICAL_FEATURE_NAMES[idx]: round(float(imp), 4)
        for idx, imp in enumerate(rf.feature_importances_)
    }
    sorted_importances = dict(sorted(feature_importances.items(), key=lambda x: x[1], reverse=True))

    metadata = {
        "model_version": "canonical-rf-v1.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(df),
        "train_records": len(train_df),
        "test_records": len(test_df),
        "features": list(CANONICAL_FEATURE_NAMES),
        "feature_importances": sorted_importances,
        "metrics": {
            "temporal_benchmark": {
                "random_forest": rf_metrics,
                "isolation_forest": iso_metrics
            },
            "cardholder_disjoint_benchmark": {
                "random_forest": rf_disjoint_metrics,
                "train_cards_count": len(train_cards),
                "test_cards_count": len(test_cards)
            }
        }
    }
    with open(MODELS_DIR / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n[Artifacts Serialized] Successfully saved:\n - {CANONICAL_MODEL_PATH}\n - {CANONICAL_SCALER_PATH}\n - {CANONICAL_ISOLATION_PATH}\n - {MODELS_DIR / 'model_metadata.json'}")

if __name__ == "__main__":
    run_canonical_training()
