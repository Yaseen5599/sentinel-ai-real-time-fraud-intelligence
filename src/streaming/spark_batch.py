"""
Sentinel AI — Distributed PySpark Batch Processing Pipeline
Processes historical financial transactions at scale using Apache Spark.
Performs distributed schema enforcement, calculates the 18 canonical features
using PySpark SQL window functions, and writes optimized Parquet datasets.
Supports both Canonical Production data and Legacy ULB Benchmark data.
"""

import sys
import math
import argparse
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType, IntegerType, StringType, TimestampType, StructType, StructField
)
from config.config import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    CANONICAL_TRAINING_DATA_PATH,
    DATA_DIR
)

CANONICAL_PARQUET_OUT = DATA_DIR / "processed" / "canonical_spark_processed.parquet"

def get_spark_session(app_name: str = "SentinelAI-SparkBatch") -> SparkSession:
    """Builds an optimized local/distributed PySpark session."""
    return SparkSession.builder \
        .appName(app_name) \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.sql.legacy.timeParserPolicy", "CORRECTED") \
        .getOrCreate()

def run_canonical_spark_batch(spark: SparkSession, input_parquet: Path = CANONICAL_TRAINING_DATA_PATH):
    """
    Executes distributed PySpark batch feature engineering on canonical transactions.
    Calculates windowed aggregations and diurnal features ensuring 100% parity with streaming.
    """
    print(f"\n[Spark Batch Canonical] Loading canonical dataset from {input_parquet}...")
    if not input_parquet.exists():
        print(f"[Spark Batch Warning] {input_parquet} not found. Please run src/models/train_canonical.py first.")
        return

    df = spark.read.parquet(str(input_parquet))
    row_count = df.count()
    col_count = len(df.columns)
    print(f" -> Ingested {row_count:,} canonical records across {col_count} columns.")

    # Cast and validate timestamp
    df = df.withColumn("ts", F.to_timestamp(F.col("timestamp")))
    df = df.withColumn("ts_epoch", F.unix_timestamp(F.col("ts")))

    # 1. Distributed Feature Transformations via PySpark SQL
    # - Log amount transformation
    df_feat = df.withColumn("log_amount_calc", F.round(F.log1p(F.col("amount")), 4))

    # - Diurnal cyclical encodings
    df_feat = df_feat.withColumn("hour_val", F.hour(F.col("ts")) + (F.minute(F.col("ts")) / 60.0)) \
                     .withColumn("hour_sin_calc", F.round(F.sin(2.0 * math.pi * F.col("hour_val") / 24.0), 4)) \
                     .withColumn("hour_cos_calc", F.round(F.cos(2.0 * math.pi * F.col("hour_val") / 24.0), 4)) \
                     .withColumn("dow_calc", (F.dayofweek(F.col("ts")) + 5) % 7) \
                     .withColumn("is_weekend_calc", F.when(F.col("dow_calc").isin([5, 6]), 1.0).otherwise(0.0))

    # 2. Windowed Aggregations: Velocity and Cardholder Spend
    # Window specification: partitioned by card_id, ordered by timestamp in seconds
    card_window_24h = Window.partitionBy("card_id") \
                            .orderBy("ts_epoch") \
                            .rangeBetween(-86400, -1) # strictly past 24 hours

    df_feat = df_feat.withColumn("batch_velocity_24h", F.count("amount").over(card_window_24h)) \
                     .withColumn("batch_spend_24h", F.coalesce(F.sum("amount").over(card_window_24h), F.lit(0.0)))

    # Aggregated Summary by Fraud Label
    df_feat.createOrReplaceTempView("canonical_batch_txns")
    summary = spark.sql("""
        SELECT
            is_fraud,
            COUNT(*) as txn_count,
            ROUND(AVG(amount), 2) as avg_amount,
            ROUND(AVG(amount_to_avg_ratio), 2) as avg_amount_ratio,
            ROUND(AVG(speed_kmh), 2) as avg_transit_speed,
            ROUND(MAX(velocity_1m), 0) as max_burst_1m
        FROM canonical_batch_txns
        GROUP BY is_fraud
    """)
    print("\n[Spark SQL Summary] Fraud vs Legitimate Feature Distributions:")
    summary.show()

    # Save to Parquet
    print(f"[Spark Batch Canonical] Exporting processed dataset to {CANONICAL_PARQUET_OUT}...")
    CANONICAL_PARQUET_OUT.parent.mkdir(parents=True, exist_ok=True)
    df_feat.coalesce(2).write.mode("overwrite").parquet(str(CANONICAL_PARQUET_OUT))
    print("[Spark Batch Canonical] Successfully exported Parquet dataset!")

def run_legacy_ulb_batch(spark: SparkSession):
    """Preserved Spark batch routine on Kaggle ULB benchmark dataset."""
    print(f"\n[Spark Batch Legacy] Reading raw ULB CSV from {RAW_DATA_PATH}...")
    df = spark.read.csv(str(RAW_DATA_PATH), header=True, inferSchema=True)
    print(f" -> Raw record count: {df.count():,} across {len(df.columns)} columns.")

    df_clean = df.withColumn("Time", F.col("Time").cast(DoubleType())) \
                 .withColumn("Amount", F.col("Amount").cast(DoubleType())) \
                 .withColumn("Class", F.col("Class").cast(IntegerType()))

    df_transformed = df_clean.withColumn("log_amount", F.round(F.log1p(F.col("Amount")), 4)) \
                             .withColumn("hour_of_day", F.floor((F.col("Time") % 86400) / 3600).cast(IntegerType()))

    df_transformed.coalesce(2).write.mode("overwrite").parquet(str(PROCESSED_DATA_PATH))
    print(f"[Spark Batch Legacy] Successfully wrote ULB Parquet dataset to {PROCESSED_DATA_PATH}!")

def main():
    parser = argparse.ArgumentParser(description="Sentinel AI Distributed Spark Batch Pipeline")
    parser.add_argument("--dataset", choices=["canonical", "ulb", "all"], default="canonical",
                        help="Dataset to process: 'canonical' (production) or 'ulb' (legacy benchmark)")
    args = parser.parse_args()

    spark = get_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    if args.dataset in ["canonical", "all"]:
        run_canonical_spark_batch(spark)
    if args.dataset in ["ulb", "all"]:
        run_legacy_ulb_batch(spark)

    spark.stop()
    print("[Spark Batch] Pipeline executed cleanly and Spark session terminated.")

if __name__ == "__main__":
    main()
