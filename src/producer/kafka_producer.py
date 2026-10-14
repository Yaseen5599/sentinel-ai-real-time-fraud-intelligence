"""
Kafka Transaction Producer
Publishes synthetic transaction streams to the Apache Kafka topic `credit-card-transactions`.
Includes graceful error handling when Kafka is unavailable, configurable frequency, and
scenario injection.
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from kafka import KafkaProducer
    from kafka.errors import NoBrokersAvailable, KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

from config.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    KAFKA_CANONICAL_TOPIC,
    SYNTHETIC_DATA_PATH
)
from src.producer.transaction_generator import TransactionGenerator

class TransactionKafkaProducer:
    """
    Produces serialized canonical transaction events to Kafka topic.
    Configured for reliability with acks='all', safe retries, and disk fallback.
    """

    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS, topic: str = KAFKA_CANONICAL_TOPIC):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic or KAFKA_CANONICAL_TOPIC
        self.generator = TransactionGenerator()
        self.producer = None
        self._init_producer()

    @property
    def is_connected(self) -> bool:
        return self.producer is not None

    def _init_producer(self):
        if not KAFKA_AVAILABLE:
            print("[Warning] kafka-python is not installed. Running in offline/mock mode.")
            return

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=5,
                retry_backoff_ms=500,
                request_timeout_ms=10000,
                max_block_ms=10000
            )
            print(f"[Kafka Producer] Successfully connected to Kafka at {self.bootstrap_servers} -> Authoritative Topic: '{self.topic}'")
        except NoBrokersAvailable:
            print(f"[Warning] Kafka broker unavailable at {self.bootstrap_servers}. Messages will be written to disk fallback.")
            self.producer = None
        except Exception as e:
            print(f"[Warning] Could not initialize Kafka producer: {e}")
            self.producer = None

    def send_transaction(self, txn: Dict[str, Any]) -> bool:
        """Publish a single transaction to Kafka topic or local file fallback."""
        key = txn.get("card_id", "CARD_DEFAULT")
        if self.producer:
            try:
                future = self.producer.send(self.topic, key=key, value=txn)
                # Flush to ensure immediate delivery
                future.get(timeout=5)
                return True
            except Exception as e:
                print(f"[Kafka Send Error] Could not send transaction {txn.get('transaction_id')}: {e}")
                return False
        else:
            # Fallback to appending to synthetic jsonl file
            self._save_to_file(txn)
            return True

    def flush(self):
        """Flushes buffered records to the Kafka broker."""
        if self.producer:
            try:
                self.producer.flush()
            except Exception:
                pass

    def close(self):
        """Flushes and closes the Kafka producer client."""
        if self.producer:
            try:
                self.producer.flush()
                self.producer.close()
            except Exception:
                pass

    def _save_to_file(self, txn: Dict[str, Any]):
        """Persist transaction to synthetic data storage."""
        with open(SYNTHETIC_DATA_PATH, "a") as f:
            f.write(json.dumps(txn) + "\n")

    def run_stream(self, num_transactions: int = 50, delay_seconds: float = 0.5, inject_scenarios: bool = True):
        """
        Generate and publish a continuous stream of transactions with normal spending
        and periodic fraud scenarios. If num_transactions <= 0, runs indefinitely.
        """
        infinite = (num_transactions <= 0)
        target_str = "Indefinite Live Stream" if infinite else f"{num_transactions} txns"
        print(f"[Producer] Starting transaction stream -> Topic: '{self.topic}' (Mode: {target_str})", flush=True)
        count = 0
        scenario_interval = 8

        while infinite or (count < num_transactions):
            # Periodically inject a fraud scenario
            if inject_scenarios and count > 0 and count % scenario_interval == 0:
                scenario_choice = (count // scenario_interval) % 4
                if scenario_choice == 0:
                    print(f"\n[Injecting Scenario] Rapid velocity burst for CARD_007...", flush=True)
                    txns = self.generator.generate_scenario_rapid_burst("CARD_007", count=6)
                elif scenario_choice == 1:
                    print(f"\n[Injecting Scenario] Impossible travel (New York -> Singapore) for CARD_012...", flush=True)
                    txns = self.generator.generate_scenario_impossible_travel("CARD_012")
                elif scenario_choice == 2:
                    print(f"\n[Injecting Scenario] High-value abnormal spike for CARD_005...", flush=True)
                    txns = [self.generator.generate_scenario_high_value_spike("CARD_005")]
                else:
                    print(f"\n[Injecting Scenario] Account takeover at 3 AM for CARD_018...", flush=True)
                    txns = [self.generator.generate_scenario_account_takeover("CARD_018")]

                for t in txns:
                    self.send_transaction(t)
                    count += 1
                    print(f" -> Sent Scenario Txn: {t['transaction_id']} | Card: {t['card_id']} | Amt: ${t['amount']} | {t.get('scenario')}", flush=True)
                    time.sleep(delay_seconds)
            else:
                txn = self.generator.generate_normal_transaction()
                self.send_transaction(txn)
                count += 1
                print(f" -> Sent Normal Txn #{count}: {txn['transaction_id']} | Card: {txn['card_id']} | Amt: ${txn['amount']} | {txn['merchant']}", flush=True)
                time.sleep(delay_seconds)

        if self.producer:
            self.producer.flush()
        print(f"\n[Producer] Finished sending {count} transactions.", flush=True)

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
    p = TransactionKafkaProducer()
    p.run_stream(num_transactions=count, delay_seconds=delay)
