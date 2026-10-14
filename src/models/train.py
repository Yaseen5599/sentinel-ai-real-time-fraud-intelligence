"""
Offline Machine Learning Model Training and Evaluation Pipeline
Implements:
  1. Chronological time-based train/test split (strict prevention of temporal leakage)
  2. StandardScaler normalization fitted strictly on training data
  3. Logistic Regression (Baseline supervised model)
  4. Random Forest (Advanced supervised classifier)
  5. Isolation Forest (Unsupervised anomaly detection for unseen patterns)
  6. Comprehensive evaluation: Precision, Recall, F1, PR-AUC, FP per 1000 txns, Cost function
  7. Artifact serialization to models/
"""

import pickle
import time
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    confusion_matrix,
    classification_report
)

from config.config import (
    RAW_DATA_PATH,
    MODELS_DIR,
    LOGISTIC_REGRESSION_MODEL_PATH,
    RANDOM_FOREST_MODEL_PATH,
    ISOLATION_FOREST_MODEL_PATH,
    SCALER_PATH,
    ASSUMED_COST_FN,
    ASSUMED_COST_FP
)

def evaluate_classifier(name: str, y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    """Calculates all required evaluation metrics."""
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    pr_auc = average_precision_score(y_true, y_prob) if y_prob is not None else 0.0

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    total_txns = len(y_true)
    fp_per_1000 = (fp / total_txns) * 1000.0

    # Business Cost Function: Total Cost = C_FN * FN + C_FP * FP
    total_cost = (ASSUMED_COST_FN * fn) + (ASSUMED_COST_FP * fp)

    metrics = {
        "model": name,
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "pr_auc": round(float(pr_auc), 4),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "fp_per_1000": round(float(fp_per_1000), 2),
        "total_cost": round(float(total_cost), 2)
    }
    return metrics

def run_training():
    print(f"[Training] Loading raw dataset from {RAW_DATA_PATH}...")
    df = pd.read_csv(RAW_DATA_PATH)
    total_records = len(df)
    fraud_records = (df["Class"] == 1).sum()
    legit_records = (df["Class"] == 0).sum()
    fraud_pct = (fraud_records / total_records) * 100

    print(f" -> Total Records: {total_records}")
    print(f" -> Legitimate: {legit_records:,} ({100 - fraud_pct:.3f}%)")
    print(f" -> Fraud Cases: {fraud_records:,} ({fraud_pct:.3f}%) [Extreme Class Imbalance]")

    # Check missing values
    missing = df.isnull().sum().sum()
    print(f" -> Missing values found: {missing}")

    # Ensure chronological order by Time
    df = df.sort_values(by="Time").reset_index(drop=True)

    # Time-based split: First 80% for training, last 20% for test
    split_idx = int(0.80 * len(df))
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    time_split_value = train_df["Time"].max()
    print(f"\n[Time-Based Split] Split cutoff time: {time_split_value:.1f}s")
    print(f" -> Train set: {len(train_df):,} txns | Fraud: {(train_df['Class'] == 1).sum()} ({((train_df['Class'] == 1).sum()/len(train_df)*100):.3f}%)")
    print(f" -> Test set:  {len(test_df):,} txns | Fraud: {(test_df['Class'] == 1).sum()} ({((test_df['Class'] == 1).sum()/len(test_df)*100):.3f}%)")

    features = [c for c in df.columns if c not in ["Time", "Class"]]
    X_train = train_df[features].values
    y_train = train_df["Class"].values
    X_test = test_df[features].values
    y_test = test_df["Class"].values

    # Fit scaler strictly on training data
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 1. Logistic Regression
    print("\n[Model 1/3] Training Logistic Regression (Baseline)...")
    lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    lr.fit(X_train_scaled, y_train)
    lr_pred = lr.predict(X_test_scaled)
    lr_prob = lr.predict_proba(X_test_scaled)[:, 1]
    lr_metrics = evaluate_classifier("Logistic Regression", y_test, lr_pred, lr_prob)

    # 2. Random Forest
    print("\n[Model 2/3] Training Random Forest Classifier...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=12, class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(X_train_scaled, y_train)
    rf_pred = rf.predict(X_test_scaled)
    rf_prob = rf.predict_proba(X_test_scaled)[:, 1]
    rf_metrics = evaluate_classifier("Random Forest", y_test, rf_pred, rf_prob)

    # 3. Isolation Forest (Anomaly Detection on normal training transactions)
    print("\n[Model 3/3] Training Isolation Forest (Unsupervised Anomaly Detection)...")
    X_train_normal = X_train_scaled[y_train == 0]
    iso = IsolationForest(n_estimators=100, contamination=0.002, random_state=42, n_jobs=-1)
    iso.fit(X_train_normal)

    # Isolation forest predicts -1 for anomalies, +1 for normal
    iso_scores = -iso.score_samples(X_test_scaled)  # higher score = more anomalous
    iso_pred = np.where(iso.predict(X_test_scaled) == -1, 1, 0)
    iso_metrics = evaluate_classifier("Isolation Forest", y_test, iso_pred, iso_scores)

    # Print Results Table
    print("\n========================= MODEL EVALUATION RESULTS =========================")
    metrics_list = [lr_metrics, rf_metrics, iso_metrics]
    results_df = pd.DataFrame(metrics_list)
    print(results_df[["model", "precision", "recall", "f1_score", "pr_auc", "fp_per_1000", "total_cost"]].to_string(index=False))
    print("============================================================================")

    # Save artifacts
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOGISTIC_REGRESSION_MODEL_PATH, "wb") as f:
        pickle.dump(lr, f)
    with open(RANDOM_FOREST_MODEL_PATH, "wb") as f:
        pickle.dump(rf, f)
    with open(ISOLATION_FOREST_MODEL_PATH, "wb") as f:
        pickle.dump(iso, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    print(f"\n[Artifacts] Successfully saved models to {MODELS_DIR}:")
    print(f" -> {LOGISTIC_REGRESSION_MODEL_PATH.name}")
    print(f" -> {RANDOM_FOREST_MODEL_PATH.name}")
    print(f" -> {ISOLATION_FOREST_MODEL_PATH.name}")
    print(f" -> {SCALER_PATH.name}")

    return metrics_list

if __name__ == "__main__":
    run_training()
