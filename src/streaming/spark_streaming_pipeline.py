"""
Sentinel AI — Distributed Spark Structured Streaming & Real-Time Fraud Engine
Consumes canonical transactions from Apache Kafka topic 'transactions-canonical',
executes genuine PySpark Structured Streaming with watermark and micro-batch processing,
derives canonical features with zero train-serve skew, evaluates the production Random Forest,
Personalized Behavioral Baseline, and Deterministic Fraud Rules, computes the hybrid risk score,
and persists records into decoupled PostgreSQL storage.

Includes:
- Genuine PySpark Structured Streaming pipeline (Kafka readStream, schema validation, event-time watermark).
- Micro-batch foreachBatch persistence to decoupled PostgreSQL (transactions, fraud_predictions, investigations).
- Strict idempotency and deduplication (prevents double-counting in sliding windows and behavioral baselines).
- Graceful standalone in-process fallback with explicit engine attribution.
- Shared runtime telemetry exported to logs/streaming_pipeline_telemetry.json for pipeline health monitoring.
"""

import os
import sys
import json
import time
import pickle
import threading
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    KAFKA_CANONICAL_TOPIC,
    KAFKA_CONSUMER_GROUP,
    CANONICAL_MODEL_PATH,
    CANONICAL_SCALER_PATH,
    RANDOM_FOREST_MODEL_PATH,
    SCALER_PATH,
    LOGS_DIR
)
from src.features.canonical_features import CanonicalFeatureExtractor, CANONICAL_FEATURE_NAMES
from src.features.behavioral_features import CardBehaviorProfile
from src.features.behavior_score import BehaviorScorer
from src.rules.fraud_rules import FraudRuleEngine
from src.models.hybrid_scorer import HybridFraudScorer
from src.database.db_client import DatabaseClient

TELEMETRY_FILE = LOGS_DIR / "streaming_pipeline_telemetry.json"

# Check Kafka client availability
try:
    from kafka import KafkaConsumer
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

# Check PySpark availability
try:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, DoubleType, TimestampType, IntegerType
    )
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False

# Explicit canonical event schema for Spark Structured Streaming
if PYSPARK_AVAILABLE:
    CANONICAL_STREAMING_SCHEMA = StructType([
        StructField("transaction_id", StringType(), False),
        StructField("idempotency_key", StringType(), True),
        StructField("card_id", StringType(), False),
        StructField("account_id", StringType(), True),
        StructField("amount", DoubleType(), False),
        StructField("currency", StringType(), True),
        StructField("channel", StringType(), True),
        StructField("merchant_id", StringType(), True),
        StructField("merchant_name", StringType(), True),
        StructField("merchant", StringType(), True),
        StructField("merchant_category_code", StringType(), True),
        StructField("city", StringType(), True),
        StructField("country", StringType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("location", StringType(), True),
        StructField("device_fingerprint", StringType(), True),
        StructField("authorization_status", StringType(), True),
        StructField("status", StringType(), True),
        StructField("timestamp", StringType(), False),
        StructField("scenario", StringType(), True)
    ])
else:
    CANONICAL_STREAMING_SCHEMA = None


class TimeAwareDedupCache:
    """
    Time-aware and size-bounded deduplication cache.
    Retains event signatures across a supported replay retention window (default: 30 minutes / 1800s),
    ensuring that replayed or retried events within the 10-minute Spark watermark are never evicted
    prematurely, while safely bounding memory growth under sustained long-running streams.
    """
    def __init__(self, retention_seconds: float = 1800.0, max_capacity: int = 50000):
        self.retention_seconds = retention_seconds
        self.max_capacity = max_capacity
        self._entries: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def add(self, key: str, event_time: Optional[float] = None) -> None:
        if not key:
            return
        now = event_time if event_time is not None else time.time()
        with self._lock:
            self._entries[key] = now
            self._prune(now)

    def contains(self, key: str, now: Optional[float] = None) -> bool:
        if not key:
            return False
        curr_time = now if now is not None else time.time()
        with self._lock:
            if key not in self._entries:
                return False
            ts = self._entries[key]
            if (curr_time - ts) <= self.retention_seconds:
                return True
            else:
                del self._entries[key]
                return False

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def _prune(self, now: float) -> None:
        cutoff = now - self.retention_seconds
        # Pop expired items from front of OrderedDict (oldest first)
        while self._entries and next(iter(self._entries.values())) < cutoff:
            self._entries.popitem(last=False)
        # Enforce max capacity safeguard
        while len(self._entries) > self.max_capacity:
            self._entries.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class RealTimeStreamProcessor:
    """
    Production real-time stream processing engine evaluating canonical transactions
    with zero train-serve feature skew, idempotent deduplication, and decoupled persistence.
    Supports both genuine PySpark Structured Streaming and an in-process micro-batch runner.
    """

    def __init__(self, use_canonical: bool = True):
        # 1. Load ML Model & Scaler
        model_path = CANONICAL_MODEL_PATH if (use_canonical and CANONICAL_MODEL_PATH.exists()) else RANDOM_FOREST_MODEL_PATH
        scaler_path = CANONICAL_SCALER_PATH if (use_canonical and CANONICAL_SCALER_PATH.exists()) else SCALER_PATH

        self.is_canonical = (model_path == CANONICAL_MODEL_PATH)

        if model_path.exists():
            with open(model_path, "rb") as f:
                self.ml_model = pickle.load(f)
            print(f"[Streaming Engine] Loaded ML model: {model_path.name} (Canonical: {self.is_canonical})")
        else:
            self.ml_model = None
            print(f"[Streaming Engine Warning] Model not found at {model_path}. Using baseline heuristic.")

        if scaler_path.exists():
            with open(scaler_path, "rb") as f:
                self.scaler = pickle.load(f)
        else:
            self.scaler = None

        # 2. Components
        self.feature_extractor = CanonicalFeatureExtractor()
        self.rule_engine = FraudRuleEngine()
        self.behavior_scorer = BehaviorScorer()
        self.hybrid_scorer = HybridFraudScorer()
        self.db_client = DatabaseClient()
        self.db_client.init_tables()

        # 3. State Management & Sliding Windows
        self.card_profiles: Dict[str, CardBehaviorProfile] = {}
        self.card_histories: Dict[str, List[Dict[str, Any]]] = {}
        self.merchant_history: List[Dict[str, Any]] = []

        self.window_1m: List[Dict[str, Any]] = []
        self.window_10m: List[Dict[str, Any]] = []
        self.window_24h: List[Dict[str, Any]] = []

        # 4. Idempotency & Deduplication Cache (Milestone 3: Time-Aware Bounded Retention)
        self._seen_tx_ids: TimeAwareDedupCache = TimeAwareDedupCache(retention_seconds=1800.0, max_capacity=50000)
        self._seen_idemp_keys: TimeAwareDedupCache = TimeAwareDedupCache(retention_seconds=1800.0, max_capacity=50000)

        # 5. Performance Metrics & Telemetry
        self.processed_count = 0
        self.total_latency_ms = 0.0
        self.spark_session: Optional[Any] = None
        self.spark_query: Optional[Any] = None
        self.active_engine = "In-Process Micro-Batch"

    def _get_or_create_profile(self, card_id: str) -> CardBehaviorProfile:
        if card_id not in self.card_profiles:
            self.card_profiles[card_id] = CardBehaviorProfile(card_id)
        return self.card_profiles[card_id]

    def _compute_ml_score(self, txn: Dict[str, Any], card_history: List[Dict[str, Any]]) -> float:
        """
        Computes ML fraud probability using the production classifier on canonical features.
        Preserves causal temporal order (only past transactions considered).
        """
        if self.ml_model is None or self.scaler is None:
            amt = float(txn.get("amount", 0.0))
            return min(1.0, amt / 1000.0)

        if self.is_canonical:
            feats = self.feature_extractor.extract_features(txn, card_history=card_history)
            vec = self.feature_extractor.to_feature_vector(feats).reshape(1, -1)
            scaled_vec = self.scaler.transform(vec)
            prob = self.ml_model.predict_proba(scaled_vec)[0, 1]
            return float(prob)
        else:
            amt = float(txn.get("amount", 0.0))
            features = np.zeros(29)
            features[-1] = amt
            scaled_feat = self.scaler.transform([features])
            prob = self.ml_model.predict_proba(scaled_feat)[0, 1]
            return float(prob)

    def process_transaction(self, txn: Dict[str, Any], engine_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes a single transaction event end-to-end:
        - Checks idempotency: rejects duplicate processing to protect behavioral profiles from inflation.
        - Evaluates sliding window aggregations, behavioral baseline, rules, and canonical ML.
        - Computes hybrid risk score and persists to decoupled storage.
        """
        start_time = time.perf_counter()

        txn_id = txn.get("transaction_id", f"TX_{int(time.time()*1000)}")
        idemp_key = txn.get("idempotency_key", f"IDEMP_{txn_id}")
        card_id = txn.get("card_id", "CARD_UNKNOWN")
        amount = float(txn.get("amount", 0.0))
        merchant = txn.get("merchant_name") or txn.get("merchant", "Unknown")
        location = txn.get("city") or txn.get("location", "Unknown")

        # ----------------------------------------------------------------------
        # Milestone 3: Idempotency & Deduplication Guard
        # ----------------------------------------------------------------------
        is_duplicate = (txn_id in self._seen_tx_ids) or (idemp_key in self._seen_idemp_keys)
        if is_duplicate:
            # Duplicate event detected: retrieve existing scored result without re-updating baselines
            existing_db = self.db_client.get_transaction(txn_id)
            if existing_db:
                existing_db["is_duplicate"] = True
                existing_db["persisted_to_db"] = True
                existing_db["storage_mode"] = "database"
                return existing_db
            for mem_t in self.db_client._memory_transactions:
                if mem_t.get("transaction_id") == txn_id or mem_t.get("idempotency_key") == idemp_key:
                    res_copy = dict(mem_t)
                    res_copy["is_duplicate"] = True
                    return res_copy

        # Timestamp normalization (Fix 4)
        raw_ts = txn.get("timestamp")
        if raw_ts is None or raw_ts == "":
            ts = datetime.now(timezone.utc)
        elif isinstance(raw_ts, datetime):
            ts = raw_ts if raw_ts.tzinfo else raw_ts.replace(tzinfo=timezone.utc)
        elif isinstance(raw_ts, (int, float)):
            try:
                sec = float(raw_ts) / 1000.0 if float(raw_ts) > 1e11 else float(raw_ts)
                ts = datetime.fromtimestamp(sec, tz=timezone.utc)
            except Exception:
                raise ValueError(f"Invalid numeric epoch timestamp: {raw_ts}")
        elif isinstance(raw_ts, str):
            clean_str = raw_ts.strip().replace("Z", "+00:00")
            parsed = None
            try:
                parsed = datetime.fromisoformat(clean_str)
            except ValueError:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
                    try:
                        parsed = datetime.strptime(raw_ts.strip(), fmt).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        pass
            if parsed is None:
                raise ValueError(f"Invalid timestamp format: '{raw_ts}'. Cannot safely parse event time.")
            ts = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        else:
            raise ValueError(f"Unsupported timestamp type {type(raw_ts).__name__}: {raw_ts}")

        # Propagate normalized ISO timestamp back to transaction dictionary before feature extraction
        txn["timestamp"] = ts.isoformat()

        # 1. Update sliding window buffers (strictly prior to adding current event for burst calculation)
        one_min_ago = ts - timedelta(minutes=1)
        ten_min_ago = ts - timedelta(minutes=10)
        twenty_four_hours_ago = ts - timedelta(hours=24)

        # Evict old events
        self.window_1m = [t for t in self.window_1m if t["timestamp"] >= one_min_ago]
        self.window_10m = [t for t in self.window_10m if t["timestamp"] >= ten_min_ago]
        self.window_24h = [t for t in self.window_24h if t["timestamp"] >= twenty_four_hours_ago]

        card_1m_burst = sum(1 for t in self.window_1m if t["card_id"] == card_id)
        card_10m_spend = sum(t["amount"] for t in self.window_10m if t["card_id"] == card_id)
        card_24h_spend = sum(t["amount"] for t in self.window_24h if t["card_id"] == card_id)

        # 2. Cardholder behavioral baseline (calculated strictly prior to adding current txn)
        profile = self._get_or_create_profile(card_id)
        card_hist = self.card_histories.get(card_id, [])

        beh_features = profile.get_features_for_transaction(txn)
        beh_features["window_1m_burst_count"] = card_1m_burst
        beh_features["window_10m_velocity_spend"] = card_10m_spend
        beh_features["window_24h_daily_spend"] = card_24h_spend

        # 3. Behavioral Anomaly Score
        behavior_score, behavior_explanations = self.behavior_scorer.calculate(beh_features)

        # 4. Supervised ML Score (Canonical features, strict temporal causality)
        ml_score = self._compute_ml_score(txn, card_history=card_hist)

        # 5. Deterministic Rules
        txn_rule_context = {
            **txn,
            "avg_amount": beh_features.get("avg_amount", 75.0),
            "usual_hours": beh_features.get("usual_hours", list(range(7, 23))),
            "frequent_merchants": beh_features.get("frequent_merchants", [])
        }
        rule_score, triggered_rules, rule_explanations = self.rule_engine.evaluate(
            txn_rule_context,
            card_history=profile.history,
            merchant_history=self.merchant_history
        )

        # 6. Hybrid Risk Score (0.5 ML + 0.3 Behavior + 0.2 Rule)
        result = self.hybrid_scorer.calculate_score(
            ml_score=ml_score,
            behavior_score=behavior_score,
            rule_score=rule_score,
            rule_explanations=rule_explanations,
            behavior_explanations=behavior_explanations
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        self.processed_count += 1
        self.total_latency_ms += elapsed_ms

        # 7. Record payload for decoupled persistence
        db_record = {
            "transaction_id": txn_id,
            "idempotency_key": idemp_key,
            "card_id": card_id,
            "account_id": txn.get("account_id", f"ACC_{card_id[-3:] if len(card_id)>=3 else '001'}"),
            "amount": amount,
            "currency": txn.get("currency", "USD"),
            "channel": txn.get("channel", "ONLINE_ECOMMERCE"),
            "merchant_name": merchant,
            "merchant": merchant,
            "city": location,
            "location": location,
            "latitude": txn.get("latitude"),
            "longitude": txn.get("longitude"),
            "timestamp": ts.isoformat(),
            "authorization_status": txn.get("authorization_status", "AUTHORIZED"),
            "ml_score": result["ml_score"],
            "behavior_score": result["behavior_score"],
            "rule_score": result["rule_score"],
            "final_fraud_score": result["final_fraud_score"],
            "fraud_decision": result["fraud_decision"],
            "triggered_rules": triggered_rules,
            "explanation": result["explanation"],
            "processing_latency_ms": round(elapsed_ms, 2),
            "is_duplicate": False,
            "streaming_engine": engine_source or self.active_engine
        }

        # Persist to decoupled database
        persisted = self.db_client.insert_transaction(db_record)
        db_record["persisted_to_db"] = bool(persisted)
        db_record["storage_mode"] = "database" if persisted else "in_memory_buffer"

        # 8. Append to sliding windows and historical state ONLY after scoring & deduplication
        w_event = {"card_id": card_id, "amount": amount, "timestamp": ts, "merchant": merchant, "location": location}
        self.window_1m.append(w_event)
        self.window_10m.append(w_event)
        self.window_24h.append(w_event)

        profile.update(txn)
        if card_id not in self.card_histories:
            self.card_histories[card_id] = []
        self.card_histories[card_id].append(txn)
        if len(self.card_histories[card_id]) > 500:
            self.card_histories[card_id] = self.card_histories[card_id][-500:]

        self.merchant_history.append({"card_id": card_id, "merchant": merchant, "timestamp": ts})
        if len(self.merchant_history) > 500:
            self.merchant_history = self.merchant_history[-500:]

        # Mark seen with time-aware retention
        event_epoch = ts.timestamp() if hasattr(ts, "timestamp") else time.time()
        self._seen_tx_ids.add(txn_id, event_epoch)
        if idemp_key:
            self._seen_idemp_keys.add(idemp_key, event_epoch)

        return db_record

    def update_telemetry(self,
                         engine: str,
                         spark_active: bool,
                         last_batch_id: Optional[int] = None,
                         batch_size: Optional[int] = None,
                         last_batch_size: Optional[int] = None,
                         input_rows_per_second: Optional[float] = None,
                         processed_rows_per_second: Optional[float] = None,
                         last_failure_reason: Optional[str] = None):
        """Emits persistent streaming worker health telemetry for API monitoring."""
        self.active_engine = engine
        effective_batch_size = last_batch_size if last_batch_size is not None else batch_size
        avg_lat = round(self.total_latency_ms / self.processed_count, 2) if self.processed_count > 0 else None
        try:
            telemetry = {
                "engine": engine,
                "spark_active": bool(spark_active),
                "status": "healthy" if not last_failure_reason else "degraded",
                "topic": KAFKA_CANONICAL_TOPIC,
                "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
                "processed_count": self.processed_count,
                "avg_latency_ms": avg_lat,
                "last_batch_id": last_batch_id,
                "last_batch_size": effective_batch_size,
                "input_rows_per_second": input_rows_per_second,
                "processed_rows_per_second": processed_rows_per_second,
                "last_failure_reason": last_failure_reason,
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "is_database_connected": self.db_client.is_connected,
                "pid": os.getpid()
            }
            TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TELEMETRY_FILE, "w") as f:
                json.dump(telemetry, f, indent=2)
        except Exception:
            pass

    # ==========================================================================
    # Milestone 2: Genuine PySpark Structured Streaming Execution
    # ==========================================================================

    def create_spark_session(self, app_name: str = "SentinelAI-SparkStructuredStreaming") -> Any:
        """
        Builds a production SparkSession configured with the official Kafka connector.
        """
        if not PYSPARK_AVAILABLE:
            raise RuntimeError("PySpark is not installed in the environment.")

        builder = SparkSession.builder \
            .appName(app_name) \
            .master(os.getenv("SPARK_MASTER", "local[2]")) \
            .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "2g")) \
            .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "2")) \
            .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")

        spark_jars = os.getenv("SPARK_JARS")
        if not spark_jars:
            jars_dir = PROJECT_ROOT / "jars"
            if jars_dir.exists():
                local_jars = sorted([str(p.resolve()) for p in jars_dir.glob("*.jar")])
                if local_jars:
                    spark_jars = ",".join(local_jars)

        if spark_jars:
            builder = builder.config("spark.jars", spark_jars)
        else:
            builder = builder.config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0")

        spark = builder.getOrCreate()
        spark.sparkContext.setLogLevel("WARN")
        self.spark_session = spark
        return spark

    def ensure_kafka_topic_ready(
        self,
        bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS,
        topic: str = KAFKA_CANONICAL_TOPIC,
        partitions: int = 3,
        replication_factor: int = 1,
        max_attempts: int = 30,
        retry_delay: float = 2.0
    ) -> bool:
        """
        Reliable Kafka readiness and topic verification mechanism.
        Verifies broker connectivity, topic existence, and valid partitions before Spark begins consuming.
        Does not treat an open TCP port or running container as proof that the required topic is ready.
        """
        if not KAFKA_AVAILABLE:
            print("[Kafka Readiness Warning] kafka-python library is unavailable to verify topic.")
            return True

        print(f"[Kafka Readiness] Verifying Kafka broker at '{bootstrap_servers}' and topic '{topic}'...")

        for attempt in range(1, max_attempts + 1):
            admin_client = None
            consumer = None
            try:
                # 1. Probe broker connection with KafkaAdminClient
                admin_client = KafkaAdminClient(
                    bootstrap_servers=bootstrap_servers,
                    request_timeout_ms=3000,
                    client_id="sentinel_readiness_admin"
                )

                # 2. Check partition metadata using KafkaConsumer
                consumer = KafkaConsumer(
                    bootstrap_servers=bootstrap_servers,
                    request_timeout_ms=3000,
                    client_id="sentinel_readiness_consumer"
                )
                existing_parts = consumer.partitions_for_topic(topic)

                if existing_parts is not None and len(existing_parts) > 0:
                    print(f"[Kafka Readiness] Verified: Topic '{topic}' exists with {len(existing_parts)} partition(s).")
                    return True

                # 3. Topic missing or has no partitions: attempt explicit creation
                print(f"[Kafka Readiness] Topic '{topic}' not found in broker metadata (attempt {attempt}/{max_attempts}). Creating...")
                try:
                    new_topic = NewTopic(name=topic, num_partitions=partitions, replication_factor=replication_factor)
                    admin_client.create_topics(new_topics=[new_topic], validate_only=False)
                    print(f"[Kafka Readiness] Issued creation request for topic '{topic}' with {partitions} partitions.")
                except TopicAlreadyExistsError:
                    pass
                except Exception as ce:
                    print(f"[Kafka Readiness Warning] Topic creation attempt returned: {ce}")

                time.sleep(1.0)
                recheck_parts = consumer.partitions_for_topic(topic)
                if recheck_parts is not None and len(recheck_parts) > 0:
                    print(f"[Kafka Readiness] Confirmed: Topic '{topic}' is ready with {len(recheck_parts)} partition(s).")
                    return True

            except Exception as e:
                print(f"[Kafka Readiness Warning] Attempt {attempt}/{max_attempts} to verify topic '{topic}' failed: {e}")
            finally:
                if admin_client:
                    try:
                        admin_client.close()
                    except Exception:
                        pass
                if consumer:
                    try:
                        consumer.close()
                    except Exception:
                        pass

            time.sleep(retry_delay)

        err = f"Failed to confirm Kafka topic '{topic}' readiness after {max_attempts} attempts."
        print(f"[Kafka Readiness Error] {err}")
        return False

    def run_spark_streaming(self,
                            checkpoint_dir: Optional[Path] = None,
                            max_batches: Optional[int] = None,
                            timeout_seconds: Optional[int] = None,
                            starting_offsets: str = "latest") -> bool:
        """
        Executes genuine PySpark Structured Streaming:
        - readStream ingestion from Kafka topic 'transactions-canonical'.
        - Schema validation against CANONICAL_STREAMING_SCHEMA.
        - Event-time parsing and 10-minute watermarking.
        - foreachBatch micro-batch processing with decoupled PostgreSQL persistence.
        - Graceful startup and shutdown.
        """
        if not PYSPARK_AVAILABLE:
            print("[Spark Streaming Error] PySpark is unavailable. Cannot run Spark streaming.")
            return False

        # Verify Kafka readiness and topic partition existence before Spark connects
        topic_ready = self.ensure_kafka_topic_ready(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            topic=KAFKA_CANONICAL_TOPIC,
            partitions=3,
            replication_factor=1
        )
        if not topic_ready:
            err_msg = f"Kafka topic readiness check failed: topic '{KAFKA_CANONICAL_TOPIC}' is unavailable or has no partitions."
            print(f"[Spark Streaming Error] {err_msg}")
            self.update_telemetry(engine="In-Process Micro-Batch", spark_active=False, last_failure_reason=err_msg)
            return False

        print(f"[Spark Structured Streaming] Initializing Spark session with Kafka connector...")
        try:
            spark = self.create_spark_session()
        except Exception as e:
            print(f"[Spark Streaming Error] Failed to create SparkSession: {e}")
            return False

        default_ckpt = Path(os.getenv("SPARK_CHECKPOINT_DIR", str(PROJECT_ROOT / "logs" / "spark_checkpoints" / "canonical_stream")))
        ckpt_path = checkpoint_dir or default_ckpt
        ckpt_path.mkdir(parents=True, exist_ok=True)

        print(f"[Spark Structured Streaming] Ingesting from Kafka {KAFKA_BOOTSTRAP_SERVERS} -> Topic: '{KAFKA_CANONICAL_TOPIC}'")
        try:
            # 1. Kafka readStream
            df_kafka = spark.readStream \
                .format("kafka") \
                .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
                .option("subscribe", KAFKA_CANONICAL_TOPIC) \
                .option("startingOffsets", starting_offsets) \
                .option("failOnDataLoss", "false") \
                .load()

            # 2. Schema validation & JSON parsing
            df_parsed = df_kafka.select(
                F.from_json(F.col("value").cast("string"), CANONICAL_STREAMING_SCHEMA).alias("event")
            ).select("event.*") \
             .filter(F.col("transaction_id").isNotNull() & F.col("card_id").isNotNull()) \
             .withColumn("event_time", F.to_timestamp(F.col("timestamp"))) \
             .withWatermark("event_time", "10 minutes")

            batch_counter = 0

            # 3. foreachBatch processing handler
            def process_micro_batch(batch_df, batch_id):
                nonlocal batch_counter
                rows = batch_df.collect()
                batch_size = len(rows)
                if batch_size == 0:
                    self.update_telemetry(engine="Spark Structured Streaming", spark_active=True, last_batch_id=batch_id, batch_size=0)
                    return

                print(f"[Spark Batch #{batch_id}] Processing micro-batch of {batch_size} canonical transaction events...", flush=True)
                for r in rows:
                    t_dict = r.asDict()
                    try:
                        res = self.process_transaction(t_dict, engine_source="Spark Structured Streaming")
                        if res.get("fraud_decision") in ["SUSPICIOUS", "FRAUD"]:
                            print(f"   [Alert {res['fraud_decision']}] Txn: {res['transaction_id']} | Card: {res['card_id']} | Amt: ${res['amount']:.2f} | Score: {res['final_fraud_score']:.2f}")
                    except ValueError as ve:
                        print(f"   [Spark Micro-Batch Warning] Dropping malformed transaction {t_dict.get('transaction_id')}: {ve}", flush=True)
                        continue

                batch_counter += 1
                self.update_telemetry(engine="Spark Structured Streaming", spark_active=True, last_batch_id=batch_id, batch_size=batch_size)

            # 4. Start streaming query
            query = df_parsed.writeStream \
                .foreachBatch(process_micro_batch) \
                .option("checkpointLocation", str(ckpt_path)) \
                .start()

            self.spark_query = query
            self.update_telemetry(engine="Spark Structured Streaming", spark_active=True)
            print("[Spark Structured Streaming] Stream query actively running. Awaiting events...")

            # Bounded execution if timeout provided
            start_wait = time.time()
            last_heartbeat_time = time.time()
            query_failed = False
            while query.isActive:
                exc = query.exception()
                if exc:
                    query_failed = True
                    break
                if max_batches and batch_counter >= max_batches:
                    print(f"[Spark Structured Streaming] Reached max batches ({max_batches}). Stopping query cleanly.")
                    break
                if timeout_seconds and (time.time() - start_wait) >= timeout_seconds:
                    print(f"[Spark Structured Streaming] Reached timeout ({timeout_seconds}s). Stopping query cleanly.")
                    break
                if time.time() - last_heartbeat_time >= 10.0:
                    self.update_telemetry(engine="Spark Structured Streaming", spark_active=True)
                    last_heartbeat_time = time.time()
                time.sleep(0.5)

            # Verify query health upon loop exit
            exc = query.exception()
            if exc or query_failed:
                err_msg = str(exc) if exc else "Stream query terminated with execution failure"
                print(f"[Spark Structured Streaming Error] Stream execution thread terminated with exception: {err_msg}")
                self.update_telemetry(engine="In-Process Micro-Batch", spark_active=False, last_failure_reason=err_msg)
                query.stop()
                spark.stop()
                return False

            if not query.isActive and batch_counter == 0 and timeout_seconds and (time.time() - start_wait) < timeout_seconds:
                err_msg = "Stream query terminated unexpectedly before timeout without processing batches."
                print(f"[Spark Structured Streaming Error] {err_msg}")
                self.update_telemetry(engine="In-Process Micro-Batch", spark_active=False, last_failure_reason=err_msg)
                query.stop()
                spark.stop()
                return False

            query.stop()
            spark.stop()
            self.update_telemetry(engine="Spark Structured Streaming", spark_active=False)
            print(f"[Spark Structured Streaming] Query terminated cleanly ({batch_counter} batches processed) and SparkSession released.")
            return True

        except Exception as e:
            err_msg = str(e)
            print(f"[Spark Structured Streaming Error] Pipeline failed: {err_msg}")
            self.update_telemetry(engine="In-Process Micro-Batch", spark_active=False, last_failure_reason=err_msg)
            if self.spark_session:
                try:
                    self.spark_session.stop()
                except Exception:
                    pass
            return False

    # ==========================================================================
    # Standalone In-Process Fallback Consumer
    # ==========================================================================

    def run_kafka_consumer(self, max_messages: Optional[int] = None, timeout_ms: Optional[int] = None):
        """
        Consumes live canonical transactions from Kafka using the standalone in-process runner.
        Preserved as a reliable zero-overhead fallback when Spark is not active.
        Truthfully reported as 'In-Process Micro-Batch'.
        """
        if not KAFKA_AVAILABLE:
            print("[Streaming Error] kafka-python is not installed.")
            return

        topic = KAFKA_CANONICAL_TOPIC
        self.ensure_kafka_topic_ready(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, topic=topic)
        print(f"[Streaming Engine (In-Process)] Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS} -> Authoritative Topic: '{topic}'")
        consumer_kwargs = {
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
            "group_id": KAFKA_CONSUMER_GROUP,
            "auto_offset_reset": "earliest",
            "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
        }
        if timeout_ms is not None and timeout_ms > 0:
            consumer_kwargs["consumer_timeout_ms"] = timeout_ms

        consumer = KafkaConsumer(topic, **consumer_kwargs)
        print("[Streaming Engine (In-Process)] Listening for incoming transaction events...")
        self.update_telemetry(engine="In-Process Micro-Batch", spark_active=False)
        count = 0

        for msg in consumer:
            txn = msg.value
            try:
                res = self.process_transaction(txn, engine_source="In-Process Micro-Batch")
            except ValueError as ve:
                print(f"[Streaming Error] Dropping malformed transaction: {ve}", flush=True)
                continue
            count += 1
            print(f"[{res['fraud_decision']}] Txn: {res['transaction_id']} | Card: {res['card_id']} | Amt: ${res['amount']:.2f} | Score: {res['final_fraud_score']:.2f} | Latency: {res['processing_latency_ms']}ms", flush=True)
            if res["fraud_decision"] in ["SUSPICIOUS", "FRAUD"]:
                print(f"   -> Reason: {res['explanation']}", flush=True)

            self.update_telemetry(engine="In-Process Micro-Batch", spark_active=False, last_batch_size=1)

            if max_messages and count >= max_messages:
                break

        consumer.close()


if __name__ == "__main__":
    processor = RealTimeStreamProcessor()
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "spark"
    if mode == "spark":
        processor.run_spark_streaming()
    else:
        processor.run_kafka_consumer()
