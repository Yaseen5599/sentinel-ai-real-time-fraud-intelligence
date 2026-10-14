"""
Configuration settings for the Real-Time Credit Card Fraud Detection Pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Runtime Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).strip().lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "creditcard.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed" / "creditcard_processed.parquet"
SYNTHETIC_DATA_PATH = DATA_DIR / "synthetic" / "streaming_transactions.json"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
for path in [DATA_DIR / "raw", DATA_DIR / "processed", DATA_DIR / "synthetic", MODELS_DIR, LOGS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Legacy Model Artifact Paths (Preserved for ULB benchmark reproducibility)
LOGISTIC_REGRESSION_MODEL_PATH = MODELS_DIR / "logistic_regression.pkl"
RANDOM_FOREST_MODEL_PATH = MODELS_DIR / "random_forest.pkl"
ISOLATION_FOREST_MODEL_PATH = MODELS_DIR / "isolation_forest.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"

# Production Canonical Model Artifact Paths (Trained on Canonical Observable Features)
CANONICAL_MODEL_PATH = MODELS_DIR / "canonical_random_forest.pkl"
CANONICAL_ISOLATION_PATH = MODELS_DIR / "canonical_isolation_forest.pkl"
CANONICAL_SCALER_PATH = MODELS_DIR / "canonical_scaler.pkl"
CANONICAL_TRAINING_DATA_PATH = DATA_DIR / "processed" / "canonical_transactions_training.parquet"

# Kafka Settings
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "transactions-canonical")
KAFKA_CANONICAL_TOPIC = os.getenv("KAFKA_CANONICAL_TOPIC", "transactions-canonical")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "fraud-detection-group")

# PostgreSQL / Supabase Settings
DB_HOST = os.getenv("FRAUD_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("FRAUD_DB_PORT", "5433"))
DB_NAME = os.getenv("FRAUD_DB_NAME", "fraud_db")
DB_USER = os.getenv("FRAUD_DB_USER", "fraud_user")
DB_PASSWORD = os.getenv("FRAUD_DB_PASSWORD", "fraud_password")
DB_TABLE = "transactions"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Redis Baseline Cache Settings
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Hybrid Fraud Scoring Weights
WEIGHT_ML = 0.5
WEIGHT_BEHAVIOR = 0.3
WEIGHT_RULE = 0.2

# Decision Thresholds
THRESHOLD_SUSPICIOUS = float(os.getenv("THRESHOLD_SUSPICIOUS", "0.40"))
THRESHOLD_FRAUD = float(os.getenv("THRESHOLD_FRAUD", "0.70"))

# Evaluation Cost Assumptions
ASSUMED_COST_FN = 500.0   # Assumed avg loss per missed fraudulent transaction
ASSUMED_COST_FP = 15.0    # Assumed customer friction / support cost per false positive alert

