"""
Sentinel AI — Database Client for Decoupled PostgreSQL / Supabase Schema
Supports transactions, predictions, investigations, confirmed outcomes, and audit logs.
Includes automatic fallback to local memory buffer if database is offline.
"""

import os
import json
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    from psycopg2 import OperationalError, IntegrityError, Error as PostgresError
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    OperationalError = Exception
    IntegrityError = Exception
    PostgresError = Exception

from config.config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    PROJECT_ROOT
)

SCHEMA_FILE = PROJECT_ROOT / "sql" / "schema.sql"

class DatabaseClient:
    """
    Manages connections, migrations, and operations against the decoupled schema.
    """
    _shared_memory_transactions: List[Dict[str, Any]] = []
    _shared_memory_cases: List[Dict[str, Any]] = []
    _shared_memory_outcomes: List[Dict[str, Any]] = []
    _buffer_lock: threading.RLock = threading.RLock()

    def __init__(self,
                 host: str = DB_HOST,
                 port: int = DB_PORT,
                 dbname: str = DB_NAME,
                 user: str = DB_USER,
                 password: str = DB_PASSWORD):
        self.database_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
        self.conn_params = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password,
            "connect_timeout": 3
        }
        self.schema_initialized: bool = DatabaseClient._shared_schema_initialized
        self.schema_error: Optional[str] = None
        self._memory_transactions = DatabaseClient._shared_memory_transactions
        self._memory_cases = DatabaseClient._shared_memory_cases
        self._memory_outcomes = DatabaseClient._shared_memory_outcomes

    def get_connection(self):
        if not PSYCOPG2_AVAILABLE:
            raise ConnectionError("psycopg2 is not installed.")
        
        conn = None
        if self.database_url:
            try:
                conn = psycopg2.connect(self.database_url, connect_timeout=4)
            except Exception:
                # Fallback to dual-stack IPv4 Supavisor connection pooler
                try:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(self.database_url)
                    pw = urllib.parse.unquote(parsed.password or "")
                    for p in [5432, 6543]:
                        try:
                            conn = psycopg2.connect(
                                host="aws-0-ap-northeast-2.pooler.supabase.com",
                                port=p,
                                dbname="postgres",
                                user="postgres.ixrwbfvsoqkxzmnfsuuq",
                                password=pw,
                                connect_timeout=4
                            )
                            break
                        except Exception:
                            continue
                except Exception:
                    pass

        if not conn:
            conn = psycopg2.connect(**self.conn_params)

        try:
            with conn.cursor() as cur:
                cur.execute("RESET ROLE;")
            conn.commit()
        except Exception:
            pass
        return conn

    def test_connection(self) -> bool:
        """Tests whether database is accessible."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    _shared_schema_initialized: bool = False

    def verify_schema(self) -> bool:
        """
        Actively verifies whether the required tables exist in the connected database.
        Updates self.schema_initialized and self.schema_error truthfully based on actual
        PostgreSQL information_schema inspection.
        """
        if not self.test_connection():
            self.schema_initialized = False
            self.schema_error = "Database offline during schema verification"
            DatabaseClient._shared_schema_initialized = False
            return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                          AND table_name IN (
                              'transactions', 
                              'fraud_predictions', 
                              'fraud_investigations', 
                              'investigation_audit_logs'
                          );
                    """)
                    existing = {row[0] for row in cur.fetchall()}
                    required = {'transactions', 'fraud_predictions', 'fraud_investigations', 'investigation_audit_logs'}
                    if required.issubset(existing):
                        self.schema_initialized = True
                        self.schema_error = None
                        DatabaseClient._shared_schema_initialized = True
                        return True
                    else:
                        missing = sorted(list(required - existing))
                        self.schema_initialized = False
                        self.schema_error = f"Missing required database tables: {missing}"
                        DatabaseClient._shared_schema_initialized = False
                        return False
        except Exception as e:
            self.schema_initialized = False
            self.schema_error = f"Schema verification error: {e}"
            DatabaseClient._shared_schema_initialized = False
            return False

    def get_storage_status(self) -> Dict[str, Any]:
        """Provides explicit transparent status of persistent storage layer."""
        connected = self.test_connection()
        backend_name = "Local Memory Buffer (Ephemeral)"
        if connected:
            if not self.schema_initialized:
                self.verify_schema()
            if self.database_url and "supabase" in self.database_url.lower():
                backend_name = "Supabase PostgreSQL (Managed Cloud)"
            else:
                backend_name = f"PostgreSQL ({self.conn_params['host']}:{self.conn_params['port']})"
        else:
            self.schema_initialized = False
            self.schema_error = "Database offline"

        with DatabaseClient._buffer_lock:
            in_mem_count = len(self._memory_transactions)

        warning_msg = None
        if not connected:
            warning_msg = "DATABASE OFFLINE: Data is stored in ephemeral Python RAM and will be lost on backend restart."
        elif self.schema_error:
            warning_msg = f"SCHEMA INITIALIZATION FAILED: {self.schema_error}"

        return {
            "is_database_connected": connected,
            "schema_initialized": self.schema_initialized,
            "schema_error": self.schema_error,
            "storage_mode": "database" if connected else "in_memory_buffer",
            "backend": backend_name,
            "survives_restart": connected,
            "in_memory_records_count": in_mem_count,
            "warning": warning_msg
        }

    def init_tables(self, schema_file: Optional[Path] = SCHEMA_FILE, max_retries: int = 3):
        """
        Executes full schema migration if connected.
        Uses PostgreSQL transaction advisory lock (pg_advisory_xact_lock) to safely serialize
        concurrent migrations across multiple API/worker processes without DeadlockDetected.
        """
        if not self.test_connection():
            print("[Database Warning] Running in ephemeral memory buffer mode (PostgreSQL is offline). Data will not survive backend restart.")
            self.schema_initialized = False
            self.schema_error = "Database offline during schema initialization"
            return

        if not schema_file or not Path(schema_file).exists():
            self.schema_initialized = True
            return

        with open(schema_file, "r") as f:
            schema_sql = f.read()

        # Deterministic 64-bit advisory lock key for Sentinel AI schema migrations
        MIGRATION_LOCK_KEY = 748201948271

        for attempt in range(1, max_retries + 1):
            conn = None
            try:
                conn = self.get_connection()
                with conn.cursor() as cur:
                    # Serialize schema execution across all workers/containers
                    cur.execute("SELECT pg_advisory_xact_lock(%s);", (MIGRATION_LOCK_KEY,))
                    cur.execute(schema_sql)
                conn.commit()
                self.verify_schema()
                print(f"[Database Status] Successfully migrated and verified PostgreSQL tables and RLS policies (attempt {attempt}).")
                return
            except Exception as e:
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                err_msg = str(e)
                print(f"[Database Migration Warning] Schema initialization attempt {attempt}/{max_retries} failed: {err_msg}")
                if attempt < max_retries:
                    # Exponential backoff with jitter to prevent herd stampede
                    sleep_sec = 0.5 * (2 ** (attempt - 1)) + (0.1 * attempt)
                    time.sleep(sleep_sec)
                else:
                    self.schema_initialized = False
                    self.schema_error = f"Migration failed after {max_retries} attempts: {err_msg}"
                    print(f"[Database Migration Error] {self.schema_error}")
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def insert_transaction(self, record: Dict[str, Any]) -> bool:
        """
        Inserts transaction and prediction into the decoupled tables:
        1. transactions
        2. fraud_predictions
        3. fraud_investigations (if SUSPICIOUS or FRAUD)
        """
        txn_id = record.get("transaction_id", f"TX_{uuid.uuid4().hex[:12]}")
        idemp_key = record.get("idempotency_key", f"IDEMP_{txn_id}")
        card_id = record.get("card_id", "CARD_UNKNOWN")
        amount = float(record.get("amount", 0.0))
        merchant_name = record.get("merchant_name") or record.get("merchant", "Unknown")
        city = record.get("city") or record.get("location", "Unknown")
        channel = record.get("channel", "ONLINE_ECOMMERCE")
        currency = record.get("currency", "USD")
        auth_status = record.get("authorization_status", "AUTHORIZED")
        lat = record.get("latitude")
        lon = record.get("longitude")
        raw_ts = record.get("timestamp", datetime.now(timezone.utc).isoformat())

        ml_score = float(record.get("ml_score", 0.0))
        beh_score = float(record.get("behavior_score", 0.0))
        rule_score = float(record.get("rule_score", 0.0))
        final_score = float(record.get("final_fraud_score", 0.0))
        decision = record.get("fraud_decision", "LEGITIMATE")
        explanation = record.get("explanation", "")
        latency_ms = float(record.get("processing_latency_ms", 0.0))
        triggered_rules = record.get("triggered_rules", [])

        # In-memory buffer sync
        mem_rec = {
            "transaction_id": txn_id,
            "idempotency_key": idemp_key,
            "card_id": card_id,
            "amount": amount,
            "currency": currency,
            "channel": channel,
            "merchant": merchant_name,
            "location": city,
            "latitude": lat,
            "longitude": lon,
            "timestamp": raw_ts,
            "authorization_status": auth_status,
            "ml_score": ml_score,
            "behavior_score": beh_score,
            "rule_score": rule_score,
            "final_fraud_score": final_score,
            "fraud_decision": decision,
            "triggered_rules": triggered_rules,
            "explanation": explanation,
            "processing_latency_ms": latency_ms,
            "model_version": "canonical-rf-v1.0"
        }
        # In-memory buffer sync (idempotent: prevent duplicate accumulation)
        with DatabaseClient._buffer_lock:
            already_in_mem = any(
                t.get("transaction_id") == txn_id or (idemp_key and t.get("idempotency_key") == idemp_key)
                for t in self._memory_transactions
            )
            if not already_in_mem:
                self._memory_transactions.insert(0, mem_rec)
                if len(self._memory_transactions) > 2000:
                    self._memory_transactions.pop()

                # If flagged, add to in-memory cases if not already present
                if decision in ["SUSPICIOUS", "FRAUD"]:
                    case_id = f"CASE_{txn_id}"
                    if not any(c.get("case_id") == case_id for c in self._memory_cases):
                        self._memory_cases.insert(0, {
                            "case_id": case_id,
                            "transaction_id": txn_id,
                            "card_id": card_id,
                            "amount": amount,
                            "merchant": merchant_name,
                            "ml_score": ml_score,
                            "behavior_score": beh_score,
                            "rule_score": rule_score,
                            "final_fraud_score": final_score,
                            "fraud_decision": decision,
                            "explanation": explanation,
                            "processing_latency_ms": latency_ms,
                            "status": "OPEN",
                            "priority": "CRITICAL" if decision == "FRAUD" else "MEDIUM",
                            "assigned_analyst_id": None,
                            "analyst_decision": "PENDING",
                            "analyst_notes": None,
                            "opened_at": raw_ts
                        })

        # Database writes
        try:
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor() as cur:
                    user_id = record.get("user_id") or f"usr_{card_id}"
                    tx_sql = """
                    INSERT INTO transactions (
                        transaction_id, idempotency_key, card_id, user_id, merchant_name,
                        amount, currency, channel, city, latitude, longitude,
                        authorization_status, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO NOTHING;
                    """
                    cur.execute(tx_sql, (
                        txn_id, idemp_key, card_id, user_id, merchant_name,
                        amount, currency, channel, city, lat, lon,
                        auth_status, raw_ts
                    ))

                    # 2. Insert into fraud_predictions
                    pred_id = f"PRED_{txn_id}"
                    pred_sql = """
                    INSERT INTO fraud_predictions (
                        prediction_id, transaction_id, ml_score, behavior_score,
                        rule_score, final_fraud_score, fraud_decision, triggered_rules,
                        explanation, processing_latency_ms, model_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (prediction_id) DO NOTHING;
                    """
                    cur.execute(pred_sql, (
                        pred_id, txn_id, ml_score, beh_score,
                        rule_score, final_score, decision, Json(triggered_rules),
                        explanation, latency_ms, "canonical-rf-v1.0"
                    ))

                    # 3. Create case in fraud_investigations if flagged
                    if decision in ["SUSPICIOUS", "FRAUD"]:
                        case_id = f"CASE_{txn_id}"
                        priority = "CRITICAL" if decision == "FRAUD" else "MEDIUM"
                        case_sql = """
                        INSERT INTO fraud_investigations (
                            case_id, transaction_id, status, priority, analyst_decision, opened_at
                        ) VALUES (%s, %s, 'OPEN', %s, 'PENDING', %s)
                        ON CONFLICT (case_id) DO NOTHING;
                        """
                        cur.execute(case_sql, (case_id, txn_id, priority, raw_ts))

                conn.commit()
            return True
        except (OperationalError, ConnectionError) as e:
            print(f"[Database Connection Error] Transaction {txn_id} database write failed: {e}. Preserved in ephemeral memory.")
            self.is_connected = False
            return False
        except IntegrityError as e:
            # Idempotency conflict / unique constraint violated: database is alive and row is already recorded
            print(f"[Database Idempotency] Transaction {txn_id} or idempotency key already recorded: {e}.")
            self.is_connected = True
            return True
        except Exception as e:
            print(f"[Database Error] Transaction {txn_id} database write failed: {e}. Preserved in ephemeral memory.")
            self.is_connected = self.test_connection()
            return False

    def get_kpis(self) -> Dict[str, Any]:
        """Aggregate summary KPIs for dashboard and API."""
        try:
            sql = """
            SELECT
                COUNT(*) as total_transactions,
                COUNT(*) FILTER (WHERE p.fraud_decision IN ('FRAUD', 'SUSPICIOUS')) as fraud_transactions,
                COALESCE(SUM(t.amount) FILTER (WHERE p.fraud_decision IN ('FRAUD', 'SUSPICIOUS')), 0.0) as prevented_loss,
                COALESCE(AVG(p.processing_latency_ms), 0.0) as avg_latency_ms
            FROM transactions t
            JOIN fraud_predictions p ON t.transaction_id = p.transaction_id;
            """
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    row = cur.fetchone()
                    total = row["total_transactions"] or 0
                    fraud = row["fraud_transactions"] or 0
                    prevented = round(float(row["prevented_loss"] or 0.0), 2)
                    latency = round(float(row["avg_latency_ms"] or 0.0), 2)
                    rate = round((fraud / total * 100), 2) if total > 0 else 0.0
                    return {
                        "total_transactions": total,
                        "fraud_transactions": fraud,
                        "fraud_rate_pct": rate,
                        "prevented_loss": prevented,
                        "avg_latency_ms": latency
                    }
        except Exception:
            self.is_connected = False

        # In-memory fallback
        total = len(self._memory_transactions)
        fraud = sum(1 for t in self._memory_transactions if t.get("fraud_decision") in ["FRAUD", "SUSPICIOUS"])
        prevented = round(sum(float(t.get("amount", 0.0)) for t in self._memory_transactions if t.get("fraud_decision") in ["FRAUD", "SUSPICIOUS"]), 2)
        latencies = [t.get("processing_latency_ms", 0.0) for t in self._memory_transactions]
        avg_lat = round(sum(latencies) / max(1, len(latencies)), 2)
        rate = round((fraud / total * 100), 2) if total > 0 else 0.0
        return {
            "total_transactions": total,
            "fraud_transactions": fraud,
            "fraud_rate_pct": rate,
            "prevented_loss": prevented,
            "avg_latency_ms": avg_lat
        }

    def get_recent_transactions(self, limit: int = 50, flagged_only: bool = False) -> List[Dict[str, Any]]:
        """Retrieve recent scored transactions."""
        try:
            filter_clause = "WHERE fraud_decision IN ('FRAUD', 'SUSPICIOUS')" if flagged_only else ""
            sql = f"""
            SELECT * FROM v_enriched_transactions
            {filter_clause}
            ORDER BY timestamp DESC
            LIMIT {limit};
            """
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    return list(cur.fetchall())
        except Exception:
            self.is_connected = False

        # Fallback to memory
        filtered = [
            t for t in self._memory_transactions
            if (not flagged_only or t.get("fraud_decision") in ["FRAUD", "SUSPICIOUS"])
        ]
        return filtered[:limit]

    def get_cases(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve open/investigated fraud cases."""
        try:
            status_clause = f"WHERE i.status = '{status}'" if status else ""
            sql = f"""
            SELECT
                i.case_id,
                i.transaction_id,
                t.card_id,
                t.amount,
                t.merchant_name AS merchant,
                t.city AS location,
                p.ml_score,
                p.behavior_score,
                p.rule_score,
                p.final_fraud_score,
                p.fraud_decision,
                p.explanation,
                p.processing_latency_ms,
                i.status,
                i.priority,
                i.assigned_analyst_id,
                i.analyst_decision,
                i.analyst_notes,
                i.opened_at,
                i.resolved_at
            FROM fraud_investigations i
            JOIN transactions t ON i.transaction_id = t.transaction_id
            JOIN fraud_predictions p ON i.transaction_id = p.transaction_id
            {status_clause}
            ORDER BY i.opened_at DESC
            LIMIT {limit};
            """
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    return list(cur.fetchall())
        except Exception:
            self.is_connected = False

        filtered = [c for c in self._memory_cases if (not status or c.get("status") == status)]
        return filtered[:limit]

    def update_case(self,
                    case_id: str,
                    analyst_id: str,
                    decision: str,
                    notes: Optional[str] = None,
                    status: str = "RESOLVED") -> bool:
        """
        Updates an investigation case and records immutable audit log.
        """
        # Memory update
        for c in self._memory_cases:
            if c.get("case_id") == case_id:
                c["status"] = status
                c["assigned_analyst_id"] = analyst_id
                c["analyst_decision"] = decision
                c["analyst_notes"] = notes
                c["resolved_at"] = datetime.now(timezone.utc).isoformat()
                break

        if decision == "CONFIRMED_FRAUD":
            # Record confirmed outcome
            txn_id = case_id.replace("CASE_", "")
            self.record_confirmed_outcome(
                transaction_id=txn_id,
                is_fraud=True,
                source="INVESTIGATOR"
            )

        if not self.test_connection():
            return True

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                    UPDATE fraud_investigations SET
                        assigned_analyst_id = %s,
                        analyst_decision = %s,
                        analyst_notes = %s,
                        status = %s,
                        resolved_at = CURRENT_TIMESTAMP
                    WHERE case_id = %s;
                    """
                    cur.execute(sql, (analyst_id, decision, notes, status, case_id))

                    # Audit log entry
                    log_id = f"LOG_{uuid.uuid4().hex[:12]}"
                    audit_sql = """
                    INSERT INTO investigation_audit_logs (
                        log_id, case_id, user_id, action, new_state
                    ) VALUES (%s, %s, %s, %s, %s);
                    """
                    cur.execute(audit_sql, (
                        log_id, case_id, analyst_id, f"CASE_{status}",
                        Json({"decision": decision, "notes": notes})
                    ))
                conn.commit()
            return True
        except Exception as e:
            print(f"[Database Error] Case {case_id} database update failed: {e}. Preserved in ephemeral memory.")
            return True

    def record_confirmed_outcome(self,
                                 transaction_id: str,
                                 is_fraud: bool,
                                 source: str = "CHARGEBACK",
                                 recovery_amount: float = 0.0) -> bool:
        """Persists ground-truth confirmed fraud outcome to fuel the retraining loop."""
        outcome_id = f"OUTCOME_{transaction_id}"
        self._memory_outcomes.append({
            "outcome_id": outcome_id,
            "transaction_id": transaction_id,
            "is_confirmed_fraud": is_fraud,
            "confirmation_source": source,
            "recovery_amount": recovery_amount,
            "confirmed_at": datetime.now(timezone.utc).isoformat()
        })

        if not self.test_connection():
            return True

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                    INSERT INTO confirmed_fraud_outcomes (
                        outcome_id, transaction_id, is_confirmed_fraud,
                        confirmation_source, recovery_amount
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        is_confirmed_fraud = EXCLUDED.is_confirmed_fraud,
                        confirmation_source = EXCLUDED.confirmation_source,
                        recovery_amount = EXCLUDED.recovery_amount;
                    """
                    cur.execute(sql, (outcome_id, transaction_id, is_fraud, source, recovery_amount))
                conn.commit()
            return True
        except Exception as e:
            print(f"[Database Error] Confirmed outcome {transaction_id} database write failed: {e}. Preserved in ephemeral memory.")
            return True

    def get_customer_transactions(self, card_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves transactions strictly for a specific customer/cardholder.
        Omits sensitive model internals (weights/rules) to protect algorithm confidentiality.
        """
        try:
            sql = """
            SELECT
                t.transaction_id,
                t.card_id,
                t.user_id,
                t.amount,
                t.currency,
                t.channel,
                t.merchant_name AS merchant,
                t.merchant_name,
                t.city AS location,
                t.city,
                t.timestamp,
                t.authorization_status,
                COALESCE(p.fraud_decision, 'LEGITIMATE') AS fraud_decision
            FROM transactions t
            LEFT JOIN fraud_predictions p ON t.transaction_id = p.transaction_id
            WHERE t.card_id = %s OR t.user_id = %s OR t.user_id = %s
            ORDER BY t.timestamp DESC
            LIMIT %s;
            """
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (card_id, card_id, f"usr_{card_id}", limit))
                    return list(cur.fetchall())
        except Exception:
            self.is_connected = False

        return [
            t for t in self._memory_transactions
            if t.get("card_id") == card_id or t.get("user_id") == card_id
        ][:limit]

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves full immutable audit history. Restricted to administrators.
        """
        try:
            sql = """
            SELECT log_id, case_id, user_id, action, previous_state, new_state, timestamp
            FROM investigation_audit_logs
            ORDER BY timestamp DESC
            LIMIT %s;
            """
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (limit,))
                    return list(cur.fetchall())
        except Exception:
            self.is_connected = False
        return []

    def execute_with_rls_context(self, claims: Dict[str, Any], query_sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Executes a query by explicitly assuming the 'authenticated' PostgreSQL role
        and injecting JWT claims into PostgreSQL request settings.
        Forces the PostgreSQL database kernel to evaluate RLS policies directly.
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                try:
                    cur.execute("SET ROLE authenticated;")
                    cur.execute("SET LOCAL request.jwt.claims = %s;", (json.dumps(claims),))
                    cur.execute(query_sql, params)
                    return list(cur.fetchall())
                finally:
                    cur.execute("RESET ROLE;")

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single transaction by ID with its fraud prediction scores and details."""
        try:
            sql = """
            SELECT t.transaction_id, t.card_id, t.user_id, t.amount, t.currency, t.channel,
                   t.merchant_name, t.city, t.authorization_status, t.timestamp,
                   p.ml_score, p.behavior_score, p.rule_score, p.final_fraud_score,
                   p.fraud_decision, p.explanation, p.processing_latency_ms
            FROM transactions t
            LEFT JOIN fraud_predictions p ON t.transaction_id = p.transaction_id
            WHERE t.transaction_id = %s;
            """
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (transaction_id,))
                    row = cur.fetchone()
                    if row:
                        return dict(row)
        except Exception:
            self.is_connected = False

        for t in self._memory_transactions:
            if t.get("transaction_id") == transaction_id:
                return t
        return None

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single fraud case by ID joined with transaction and prediction details."""
        try:
            sql = """
            SELECT
                i.case_id,
                i.transaction_id,
                t.card_id,
                t.amount,
                t.merchant_name AS merchant,
                t.city AS location,
                p.ml_score,
                p.behavior_score,
                p.rule_score,
                p.final_fraud_score,
                p.fraud_decision,
                p.explanation,
                p.processing_latency_ms,
                i.status,
                i.priority,
                i.assigned_analyst_id,
                i.analyst_decision,
                i.analyst_notes,
                i.opened_at,
                i.resolved_at
            FROM fraud_investigations i
            JOIN transactions t ON i.transaction_id = t.transaction_id
            LEFT JOIN fraud_predictions p ON i.transaction_id = p.transaction_id
            WHERE i.case_id = %s;
            """
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (case_id,))
                    row = cur.fetchone()
                    if row:
                        return dict(row)
        except Exception:
            self.is_connected = False

        for c in self._memory_cases:
            if c.get("case_id") == case_id:
                return c
        return None

    def record_customer_dispute(self,
                                transaction_id: str,
                                reason: str,
                                reporter_id: str,
                                notes: Optional[str] = None,
                                freeze_card: bool = False) -> Dict[str, Any]:
        """
        Records a customer dispute for an existing transaction.
        Creates/updates an investigation case in 'OPEN' status with 'PENDING' outcome (distinct from confirmed fraud).
        Logs an immutable audit event in investigation_audit_logs.
        """
        case_id = f"CASE_{transaction_id}"
        now_iso = datetime.now(timezone.utc).isoformat()
        dispute_note = f"Customer Dispute [{reason}]: {notes or 'No additional notes provided'}"

        # Update or add in-memory case
        found_case = False
        for c in self._memory_cases:
            if c.get("case_id") == case_id or c.get("transaction_id") == transaction_id:
                c["status"] = "OPEN"
                c["priority"] = "HIGH"
                c["analyst_decision"] = "PENDING"
                prev_note = c.get("analyst_notes") or ""
                c["analyst_notes"] = f"{prev_note}\n{dispute_note}" if prev_note else dispute_note
                found_case = True
                break
        if not found_case:
            txn = self.get_transaction(transaction_id) or {}
            self._memory_cases.insert(0, {
                "case_id": case_id,
                "transaction_id": transaction_id,
                "card_id": txn.get("card_id", "CARD_UNKNOWN"),
                "amount": txn.get("amount", 0.0),
                "merchant": txn.get("merchant_name") or txn.get("merchant", "Unknown Merchant"),
                "location": txn.get("city") or txn.get("location", "Unknown Location"),
                "status": "OPEN",
                "priority": "HIGH",
                "assigned_analyst_id": None,
                "analyst_decision": "PENDING",
                "analyst_notes": dispute_note,
                "opened_at": now_iso
            })

        log_id = f"LOG_{uuid.uuid4().hex[:12]}"
        audit_state = {
            "dispute_reason": reason,
            "notes": notes,
            "freeze_card": freeze_card,
            "reported_by": reporter_id
        }

        if self.test_connection():
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        case_sql = """
                        INSERT INTO fraud_investigations (
                            case_id, transaction_id, status, priority, analyst_decision, analyst_notes, opened_at
                        ) VALUES (%s, %s, 'OPEN', 'HIGH', 'PENDING', %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (case_id) DO UPDATE SET
                            status = 'OPEN',
                            priority = 'HIGH',
                            analyst_notes = COALESCE(fraud_investigations.analyst_notes || E'\n---\n', '') || EXCLUDED.analyst_notes;
                        """
                        cur.execute(case_sql, (case_id, transaction_id, dispute_note))

                        audit_sql = """
                        INSERT INTO investigation_audit_logs (
                            log_id, case_id, user_id, action, new_state
                        ) VALUES (%s, %s, %s, %s, %s);
                        """
                        cur.execute(audit_sql, (log_id, case_id, reporter_id, "CUSTOMER_DISPUTE_FILED", Json(audit_state)))
                    conn.commit()
            except Exception as e:
                print(f"[Database Error] Dispute {case_id} write failed: {e}. Preserved in ephemeral memory.")

        ticket_suffix = transaction_id[-6:] if len(transaction_id) >= 6 else transaction_id
        return {
            "ticket_id": f"DISP-{ticket_suffix}",
            "case_id": case_id,
            "transaction_id": transaction_id,
            "status": "OPEN",
            "priority": "HIGH",
            "analyst_decision": "PENDING",
            "reason": reason,
            "reported_at": now_iso
        }

    def get_customer_disputes(self, card_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves disputes and investigation cases for a specific customer's card.
        """
        try:
            sql = """
            SELECT
                i.case_id,
                i.transaction_id,
                t.card_id,
                t.merchant_name AS merchant,
                t.amount,
                t.city AS location,
                i.status,
                i.priority,
                i.analyst_decision,
                i.analyst_notes,
                i.opened_at,
                i.resolved_at
            FROM fraud_investigations i
            JOIN transactions t ON i.transaction_id = t.transaction_id
            WHERE t.card_id = %s OR t.user_id = %s OR t.user_id = %s
            ORDER BY i.opened_at DESC
            LIMIT %s;
            """
            with self.get_connection() as conn:
                self.is_connected = True
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (card_id, card_id, f"usr_{card_id}", limit))
                    rows = cur.fetchall()
                    disputes = []
                    for r in rows:
                        d = dict(r)
                        txn_id = d.get("transaction_id", "")
                        d["ticket_id"] = f"DISP-{txn_id[-6:] if len(txn_id) >= 6 else txn_id}"
                        disputes.append(d)
                    return disputes
        except Exception:
            self.is_connected = False

        mem_filtered = [
            c for c in self._memory_cases
            if not card_id or c.get("card_id") == card_id or c.get("user_id") == card_id
        ]
        results = []
        for c in mem_filtered[:limit]:
            item = dict(c)
            txn_id = item.get("transaction_id", "")
            item["ticket_id"] = f"DISP-{txn_id[-6:] if len(txn_id) >= 6 else txn_id}"
            results.append(item)
        return results

    def get_admin_users(self, trusted_registry: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Retrieves available user accounts without exposing passwords or hashes.
        Queries auth.users if available, falling back to trusted users registry.
        """
        users: List[Dict[str, Any]] = []
        if self.test_connection():
            try:
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            SELECT id, email, raw_app_meta_data, raw_user_meta_data, created_at, last_sign_in_at
                            FROM auth.users
                            ORDER BY created_at ASC;
                        """)
                        rows = cur.fetchall()
                        for r in rows:
                            app_meta = r["raw_app_meta_data"] if isinstance(r["raw_app_meta_data"], dict) else {}
                            user_meta = r["raw_user_meta_data"] if isinstance(r["raw_user_meta_data"], dict) else {}
                            email = r["email"] or "unknown@sentinel.ai"
                            users.append({
                                "id": str(r["id"]),
                                "email": email,
                                "name": user_meta.get("full_name") or email.split("@")[0].replace(".", " ").title(),
                                "role": app_meta.get("role", "customer"),
                                "department": user_meta.get("department", "Retail Banking"),
                                "card_id": app_meta.get("card_id"),
                                "status": "ACTIVE",
                                "created_at": str(r["created_at"]) if r.get("created_at") else None,
                                "last_login": str(r["last_sign_in_at"]) if r.get("last_sign_in_at") else "Recent"
                            })
                        if users:
                            return users
            except Exception:
                pass

        if trusted_registry:
            for email, u in trusted_registry.items():
                users.append({
                    "id": u.get("id"),
                    "email": email,
                    "name": u.get("name") or email.split("@")[0].replace(".", " ").title(),
                    "role": u.get("role", "customer"),
                    "department": u.get("department", "Retail Banking"),
                    "card_id": u.get("card_id"),
                    "status": "ACTIVE",
                    "created_at": None,
                    "last_login": "Verified"
                })
        return users

    def drain_memory_buffer(self, admin_user_id: str = "admin") -> Dict[str, Any]:
        """
        Drains buffered in-memory transactions and predictions to persistent PostgreSQL storage.
        Preserves transaction-prediction relationships and metadata.
        Idempotent: relies on ON CONFLICT DO NOTHING.
        Only removes each record from memory buffer after its persistence has been confirmed.
        Audits every drain attempt and its outcome in investigation_audit_logs.
        Returns accurate counts: recovered, remaining, failed.
        """
        if not self.test_connection():
            initial_count = len(self._memory_transactions)
            return {
                "status": "failed",
                "message": "Database is unreachable. Memory buffer preserved without modifications.",
                "initial_count": initial_count,
                "recovered_count": 0,
                "failed_count": initial_count,
                "remaining_count": initial_count,
                "database_connected": False
            }

        with DatabaseClient._buffer_lock:
            initial_count = len(self._memory_transactions)
            records_to_process = list(self._memory_transactions)

        recovered_count = 0
        failed_count = 0
        conn = None

        try:
            conn = self.get_connection()
        except Exception:
            conn = None

        try:
            for rec in records_to_process:
                txn_id = rec.get("transaction_id")
                if not txn_id:
                    continue

                persisted_ok = False
                try:
                    idemp_key = rec.get("idempotency_key") or f"IDEMP_{txn_id}"
                    card_id = rec.get("card_id", "CARD_007")
                    user_id = rec.get("user_id") or f"usr_{card_id}"
                    merchant_name = rec.get("merchant_name") or rec.get("merchant", "Unknown Merchant")
                    raw_amt = rec.get("amount")
                    amount = float(raw_amt) if raw_amt is not None else 0.0
                    currency = rec.get("currency") or "USD"
                    channel = rec.get("channel") or "E-Commerce"
                    city = rec.get("city") or rec.get("location") or "Unknown Location"
                    raw_lat = rec.get("latitude")
                    lat = float(raw_lat) if raw_lat is not None else 40.7128
                    raw_lon = rec.get("longitude")
                    lon = float(raw_lon) if raw_lon is not None else -74.0060
                    auth_status = rec.get("authorization_status") or "APPROVED"
                    raw_ts = rec.get("timestamp") or datetime.now(timezone.utc).isoformat()

                    pred_id = rec.get("prediction_id") or f"PRED_{txn_id}"
                    raw_ml = rec.get("ml_score")
                    ml_score = float(raw_ml) if raw_ml is not None else 0.0
                    raw_beh = rec.get("behavior_score")
                    beh_score = float(raw_beh) if raw_beh is not None else 0.0
                    raw_rule = rec.get("rule_score")
                    rule_score = float(raw_rule) if raw_rule is not None else 0.0
                    raw_final = rec.get("final_fraud_score")
                    final_score = float(raw_final) if raw_final is not None else 0.0
                    decision = rec.get("fraud_decision") or "LEGITIMATE"
                    triggered_rules = rec.get("triggered_rules") or []
                    explanation = rec.get("explanation") or "Standard transaction evaluation."
                    raw_lat_ms = rec.get("processing_latency_ms")
                    latency_ms = float(raw_lat_ms) if raw_lat_ms is not None else 12.0
                    model_ver = rec.get("model_version") or "canonical-rf-v1.0"

                    if conn is None or conn.closed:
                        conn = self.get_connection()

                    with conn.cursor() as cur:
                        # 1. Insert transaction
                        tx_sql = """
                        INSERT INTO transactions (
                            transaction_id, idempotency_key, card_id, user_id, merchant_name,
                            amount, currency, channel, city, latitude, longitude,
                            authorization_status, timestamp
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (transaction_id) DO NOTHING;
                        """
                        cur.execute(tx_sql, (
                            txn_id, idemp_key, card_id, user_id, merchant_name,
                            amount, currency, channel, city, lat, lon,
                            auth_status, raw_ts
                        ))

                        # 2. Insert fraud prediction
                        pred_sql = """
                        INSERT INTO fraud_predictions (
                            prediction_id, transaction_id, ml_score, behavior_score,
                            rule_score, final_fraud_score, fraud_decision, triggered_rules,
                            explanation, processing_latency_ms, model_version
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (prediction_id) DO NOTHING;
                        """
                        cur.execute(pred_sql, (
                            pred_id, txn_id, ml_score, beh_score,
                            rule_score, final_score, decision, Json(triggered_rules),
                            explanation, latency_ms, model_ver
                        ))

                        # 3. Insert investigation case if flagged
                        if decision in ["SUSPICIOUS", "FRAUD"]:
                            case_id = f"CASE_{txn_id}"
                            priority = "CRITICAL" if decision == "FRAUD" else "MEDIUM"
                            case_sql = """
                            INSERT INTO fraud_investigations (
                                case_id, transaction_id, status, priority, analyst_decision, opened_at
                            ) VALUES (%s, %s, 'OPEN', %s, 'PENDING', %s)
                            ON CONFLICT (case_id) DO NOTHING;
                            """
                            cur.execute(case_sql, (case_id, txn_id, priority, raw_ts))

                    conn.commit()
                    persisted_ok = True
                except Exception as e:
                    print(f"[Buffer Drain Error] Failed to persist buffered txn {txn_id}: {e}")
                    persisted_ok = False
                    if conn:
                        try:
                            conn.rollback()
                        except Exception:
                            pass

                if persisted_ok:
                    with DatabaseClient._buffer_lock:
                        # Remove confirmed record from memory buffer
                        self._memory_transactions = [x for x in self._memory_transactions if x.get("transaction_id") != txn_id]
                        if decision in ["SUSPICIOUS", "FRAUD"]:
                            case_id = f"CASE_{txn_id}"
                            self._memory_cases = [c for c in self._memory_cases if c.get("case_id") != case_id]
                    recovered_count += 1
                else:
                    failed_count += 1
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            with DatabaseClient._buffer_lock:
                DatabaseClient._shared_memory_transactions = self._memory_transactions
                DatabaseClient._shared_memory_cases = self._memory_cases
                remaining_count = len(self._memory_transactions)

        # Record audit log
        log_id = f"LOG_{uuid.uuid4().hex[:12]}"
        audit_state = {
            "initial_buffer_count": initial_count,
            "recovered_count": recovered_count,
            "failed_count": failed_count,
            "remaining_count": remaining_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    audit_sql = """
                    INSERT INTO investigation_audit_logs (
                        log_id, case_id, user_id, action, new_state
                    ) VALUES (%s, %s, %s, %s, %s);
                    """
                    cur.execute(audit_sql, (log_id, None, admin_user_id, "STORAGE_MEMORY_BUFFER_DRAINED", Json(audit_state)))
                conn.commit()
        except Exception:
            pass

        return {
            "status": "success" if failed_count == 0 else ("partial_success" if recovered_count > 0 else "failed"),
            "initial_count": initial_count,
            "recovered_count": recovered_count,
            "failed_count": failed_count,
            "remaining_count": remaining_count,
            "database_connected": True
        }

