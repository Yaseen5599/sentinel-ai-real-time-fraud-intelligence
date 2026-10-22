#!/usr/bin/env python3
"""
Sentinel AI — Synthetic Dataset Generation Pipeline
Generates reproducible, validated CSV datasets:
  1. data/real_data/cardholders.csv (Cardholder profiles and behavioral baselines)
  2. data/real_data/transactions_10000.csv (Exactly 10,000 chronological transactions: T00001 to T10000)

NOTICE: All generated records are strictly synthetic and for testing/benchmarking purposes only.
No real personal data, payment credentials, or production bank customer information is used.
"""

import os
import sys
import csv
import random
import math
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.producer.transaction_generator import CITY_COORDINATES, MERCHANT_CATALOG

DATA_DIR = PROJECT_ROOT / "data" / "real_data"
CARDHOLDERS_CSV = DATA_DIR / "cardholders.csv"
TRANSACTIONS_CSV = DATA_DIR / "transactions_10000.csv"

# Synthetic customer names
SYNTHETIC_FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen", "Stephen", "Anna",
    "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Alexander", "Debra",
    "Frank", "Rachel", "Patrick", "Catherine", "Raymond", "Carolyn", "Jack", "Janet"
]

SYNTHETIC_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
    "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
    "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza"
]

def generate_cardholders(num_cardholders: int = 60, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generates synthetic cardholder baseline records.
    """
    rng = random.Random(seed)
    cities = list(CITY_COORDINATES.keys())
    merchants = list(MERCHANT_CATALOG.keys())

    cardholders = []
    base_created_start = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(1, num_cardholders + 1):
        card_id = f"CARD_{i:03d}"
        customer_id = f"CUST_{i:03d}"
        fname = rng.choice(SYNTHETIC_FIRST_NAMES)
        lname = rng.choice(SYNTHETIC_LAST_NAMES)
        full_name = f"{fname} {lname}"

        account_age_days = rng.randint(90, 1800)
        usual_amount = round(rng.uniform(25.0, 140.0), 2)
        # Average transactions per day (e.g. 1.2 to 4.5)
        usual_frequency = round(rng.uniform(1.2, 4.5), 2)

        # Standard active spending window (e.g., 07:00 to 22:00)
        start_hour = rng.choice([6, 7, 8])
        end_hour = rng.choice([21, 22, 23])
        usual_active_hours = f"{start_hour:02d}:00-{end_hour:02d}:00"

        home_city = rng.choice(cities[:6])  # domestic metropolitan centers
        created_at = (base_created_start + timedelta(days=rng.randint(0, 700))).isoformat()

        # 3 frequent merchants
        frequent_merchs = rng.sample(merchants[:8], k=3)

        cardholders.append({
            "card_id": card_id,
            "customer_id": customer_id,
            "customer_name": full_name,
            "account_age_days": account_age_days,
            "usual_transaction_amount": usual_amount,
            "usual_transaction_frequency": usual_frequency,
            "usual_active_hours": usual_active_hours,
            "home_location": home_city,
            "created_at": created_at,
            # Internal baseline tracking for generator
            "_start_hour": start_hour,
            "_end_hour": end_hour,
            "_frequent_merchants": frequent_merchs
        })

    return cardholders

def generate_transactions(
    cardholders: List[Dict[str, Any]],
    total_transactions: int = 10000,
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Generates exactly 10,000 transactions (T00001 to T10000) in strict chronological order.
    Incorporates natural spending variations and realistic suspicious fraud scenarios.
    """
    rng = random.Random(seed)
    cards_map = {c["card_id"]: c for c in cardholders}
    card_ids = list(cards_map.keys())
    all_merchants = list(MERCHANT_CATALOG.keys())
    all_cities = list(CITY_COORDINATES.keys())

    # Chronological span: 45 days of financial transactions
    start_time = datetime(2026, 9, 1, 8, 0, 0, tzinfo=timezone.utc)
    curr_time = start_time

    # Track card histories to maintain logical continuity
    card_last_time: Dict[str, datetime] = {}
    card_last_loc: Dict[str, str] = {}

    transactions: List[Dict[str, Any]] = []

    # Target: ~3% suspicious transactions across diverse patterns
    # (Bursts, Impossible Travel, High Spikes, Off-Hour Spends, Card Testing)
    # We will reserve structured scenario sequences to ensure realistic multi-event patterns.
    
    # Pre-determine scenario trigger transaction indices
    suspicious_targets: Dict[int, str] = {}
    # Spread out ~60 suspicious clusters across 10,000 transactions
    step = total_transactions // 65
    scenario_types = [
        "BURST",
        "IMPOSSIBLE_TRAVEL",
        "HIGH_SPIKE",
        "UNUSUAL_TIME_AND_MERCHANT",
        "DECLINED_THEN_HIGH"
    ]

    for sc_idx in range(1, 62):
        t_pos = sc_idx * step + rng.randint(-10, 10)
        if 50 <= t_pos <= total_transactions - 20:
            sc_type = scenario_types[sc_idx % len(scenario_types)]
            suspicious_targets[t_pos] = sc_type

    i = 1
    while i <= total_transactions:
        tx_id = f"T{i:05d}"

        # Advance chronological time by average 6.5 minutes (exponential distribution)
        time_delta_sec = rng.expovariate(1.0 / 390.0)
        curr_time += timedelta(seconds=max(5.0, time_delta_sec))

        if i in suspicious_targets:
            sc_type = suspicious_targets[i]
            target_card = rng.choice(card_ids)
            card_info = cards_map[target_card]
            home_loc = card_info["home_location"]
            usual_amt = card_info["usual_transaction_amount"]

            if sc_type == "BURST" and i <= total_transactions - 5:
                # 6 rapid transactions in under 2 minutes
                burst_merch = rng.choice(["Amazon", "Target", "Starbucks", "Walmart"])
                for b_step in range(6):
                    sub_id = f"T{i:05d}"
                    curr_time += timedelta(seconds=rng.randint(8, 18))
                    amt = round(rng.uniform(15.0, 95.0), 2)
                    transactions.append({
                        "transaction_id": sub_id,
                        "card_id": target_card,
                        "amount": amt,
                        "merchant": burst_merch,
                        "location": home_loc,
                        "timestamp": curr_time.isoformat()
                    })
                    card_last_time[target_card] = curr_time
                    card_last_loc[target_card] = home_loc
                    i += 1
                continue

            elif sc_type == "IMPOSSIBLE_TRAVEL" and i <= total_transactions - 2:
                # Event 1: in home city
                sub_id1 = f"T{i:05d}"
                transactions.append({
                    "transaction_id": sub_id1,
                    "card_id": target_card,
                    "amount": round(rng.uniform(20.0, 80.0), 2),
                    "merchant": "Starbucks",
                    "location": home_loc,
                    "timestamp": curr_time.isoformat()
                })
                i += 1

                # Event 2: 15 minutes later in London, Tokyo, or Singapore (>3000 km away)
                sub_id2 = f"T{i:05d}"
                curr_time += timedelta(minutes=rng.randint(10, 20))
                overseas_loc = rng.choice(["London", "Tokyo", "Singapore", "Sydney"])
                transactions.append({
                    "transaction_id": sub_id2,
                    "card_id": target_card,
                    "amount": round(rng.uniform(150.0, 850.0), 2),
                    "merchant": "LuxuryJewelry",
                    "location": overseas_loc,
                    "timestamp": curr_time.isoformat()
                })
                card_last_time[target_card] = curr_time
                card_last_loc[target_card] = overseas_loc
                i += 1
                continue

            elif sc_type == "HIGH_SPIKE":
                # Transaction amount is 8x to 15x cardholder's usual amount at a high-risk merchant
                spike_amt = round(usual_amt * rng.uniform(8.0, 16.0), 2)
                spike_merch = rng.choice(["LuxuryJewelry", "CryptoExchange", "HighEndElectronics", "OverseasCasino"])
                transactions.append({
                    "transaction_id": tx_id,
                    "card_id": target_card,
                    "amount": spike_amt,
                    "merchant": spike_merch,
                    "location": home_loc,
                    "timestamp": curr_time.isoformat()
                })
                card_last_time[target_card] = curr_time
                card_last_loc[target_card] = home_loc
                i += 1
                continue

            elif sc_type == "UNUSUAL_TIME_AND_MERCHANT":
                # Initiated at 03:30 AM outside active hours at unfamiliar online merchant
                night_time = curr_time.replace(hour=3, minute=rng.randint(10, 50))
                if night_time < curr_time:
                    night_time += timedelta(days=1)
                curr_time = night_time
                amt = round(rng.uniform(400.0, 1200.0), 2)
                transactions.append({
                    "transaction_id": tx_id,
                    "card_id": target_card,
                    "amount": amt,
                    "merchant": rng.choice(["CryptoExchange", "OverseasCasino", "HighEndElectronics"]),
                    "location": rng.choice(all_cities),
                    "timestamp": curr_time.isoformat()
                })
                card_last_time[target_card] = curr_time
                card_last_loc[target_card] = home_loc
                i += 1
                continue

        # Standard Legitimate / Varied Ordinary Transaction
        card_id = rng.choice(card_ids)
        card_info = cards_map[card_id]
        home_loc = card_info["home_location"]
        usual_amt = card_info["usual_transaction_amount"]
        frequent_merchs = card_info["_frequent_merchants"]

        # Timestamp hour within cardholder active hours 92% of the time
        if rng.random() < 0.92:
            hour_target = rng.randint(card_info["_start_hour"], card_info["_end_hour"])
            if curr_time.hour != hour_target:
                curr_time = curr_time.replace(hour=hour_target)

        # Merchant: 75% frequent merchant, 25% other catalog merchant
        if rng.random() < 0.75:
            merchant = rng.choice(frequent_merchs)
        else:
            merchant = rng.choice(all_merchants)

        # Location: 94% home city, 6% legitimate travel city
        if rng.random() < 0.94:
            location = home_loc
        else:
            location = rng.choice(all_cities)

        # Amount: log-normal around usual amount
        amt_factor = rng.lognormvariate(0.0, 0.35)
        amount = round(max(2.50, usual_amt * amt_factor), 2)

        transactions.append({
            "transaction_id": tx_id,
            "card_id": card_id,
            "amount": amount,
            "merchant": merchant,
            "location": location,
            "timestamp": curr_time.isoformat()
        })

        card_last_time[card_id] = curr_time
        card_last_loc[card_id] = location
        i += 1

    # Ensure strictly sorted by timestamp and re-indexed to exact T00001 - T10000
    transactions.sort(key=lambda x: x["timestamp"])
    for idx, t in enumerate(transactions, start=1):
        t["transaction_id"] = f"T{idx:05d}"

    return transactions

def write_csvs(cardholders: List[Dict[str, Any]], transactions: List[Dict[str, Any]]) -> Tuple[Path, Path]:
    """Writes both datasets to disk under data/real_data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Cardholders CSV
    cardholder_fields = [
        "card_id",
        "customer_id",
        "customer_name",
        "account_age_days",
        "usual_transaction_amount",
        "usual_transaction_frequency",
        "usual_active_hours",
        "home_location",
        "created_at"
    ]
    with open(CARDHOLDERS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cardholder_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cardholders)

    # 2. Transactions CSV
    transaction_fields = [
        "transaction_id",
        "card_id",
        "amount",
        "merchant",
        "location",
        "timestamp"
    ]
    with open(TRANSACTIONS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=transaction_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(transactions)

    return CARDHOLDERS_CSV, TRANSACTIONS_CSV

def validate_datasets(cardholders_path: Path, transactions_path: Path) -> Dict[str, Any]:
    """
    Validates foreign keys, schema integrity, constraints, and chronological sorting.
    Returns validation report or raises ValueError on validation error.
    """
    errors = []

    # 1. Validate Cardholders
    if not cardholders_path.exists():
        raise FileNotFoundError(f"Cardholders CSV not found at {cardholders_path}")

    cardholders_data = []
    with open(cardholders_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            cardholders_data.append(r)

    known_card_ids = set()
    for row_idx, ch in enumerate(cardholders_data, start=2):
        cid = ch.get("card_id", "").strip()
        if not cid:
            errors.append(f"Cardholder row {row_idx}: empty card_id")
        if cid in known_card_ids:
            errors.append(f"Cardholder row {row_idx}: duplicate card_id '{cid}'")
        known_card_ids.add(cid)

        try:
            amt = float(ch.get("usual_transaction_amount", 0))
            if amt <= 0:
                errors.append(f"Cardholder {cid}: non-positive usual_transaction_amount ({amt})")
        except ValueError:
            errors.append(f"Cardholder {cid}: invalid numeric usual_transaction_amount")

    # 2. Validate Transactions
    if not transactions_path.exists():
        raise FileNotFoundError(f"Transactions CSV not found at {transactions_path}")

    transactions_data = []
    with open(transactions_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            transactions_data.append(r)

    total_txns = len(transactions_data)
    if total_txns != 10000:
        errors.append(f"Expected exactly 10,000 transaction rows, found {total_txns}")

    seen_tx_ids = set()
    prev_ts = None
    suspicious_patterns_detected = 0

    for idx, row in enumerate(transactions_data, start=1):
        expected_id = f"T{idx:05d}"
        actual_id = row.get("transaction_id", "").strip()
        if actual_id != expected_id:
            errors.append(f"Row {idx+1}: expected ID '{expected_id}', got '{actual_id}'")
        if actual_id in seen_tx_ids:
            errors.append(f"Row {idx+1}: duplicate transaction_id '{actual_id}'")
        seen_tx_ids.add(actual_id)

        # Foreign key validation
        card_id = row.get("card_id", "").strip()
        if card_id not in known_card_ids:
            errors.append(f"Row {idx+1}: card_id '{card_id}' does not exist in cardholders CSV")

        # Amount validation
        try:
            amt = float(row.get("amount", 0))
            if amt <= 0:
                errors.append(f"Row {idx+1} ({actual_id}): invalid non-positive amount ({amt})")
            if amt >= 1000.0:
                suspicious_patterns_detected += 1
        except ValueError:
            errors.append(f"Row {idx+1} ({actual_id}): amount is not a valid float")

        # Timestamp validation and chronological ordering
        raw_ts = row.get("timestamp", "").strip()
        try:
            ts = datetime.fromisoformat(raw_ts)
            if prev_ts and ts < prev_ts:
                errors.append(f"Row {idx+1} ({actual_id}): timestamp {raw_ts} is before preceding timestamp {prev_ts.isoformat()}")
            prev_ts = ts
        except Exception as e:
            errors.append(f"Row {idx+1} ({actual_id}): invalid ISO 8601 timestamp '{raw_ts}' ({e})")

        # Location format validation
        loc = row.get("location", "").strip()
        if not loc:
            errors.append(f"Row {idx+1} ({actual_id}): missing location")

        # Merchant format validation
        merch = row.get("merchant", "").strip()
        if not merch:
            errors.append(f"Row {idx+1} ({actual_id}): missing merchant")

    report = {
        "status": "PASSED" if not errors else "FAILED",
        "cardholders_count": len(cardholders_data),
        "transactions_count": total_txns,
        "suspicious_examples_detected": suspicious_patterns_detected,
        "unique_cards_active": len(set(t["card_id"] for t in transactions_data)),
        "time_span_start": transactions_data[0]["timestamp"] if transactions_data else None,
        "time_span_end": transactions_data[-1]["timestamp"] if transactions_data else None,
        "error_count": len(errors),
        "errors": errors[:20]  # truncate to first 20 errors
    }

    if errors:
        sys.stderr.write(f"\n[VALIDATION FAILED] Found {len(errors)} validation errors:\n")
        for err in errors[:10]:
            sys.stderr.write(f"  - {err}\n")
        sys.exit(1)

    return report

def main():
    print("=" * 70)
    print("Sentinel AI — 10,000 Transaction & Cardholder Dataset Generator")
    print("=" * 70)
    
    print("[1/3] Generating synthetic cardholder baseline profiles (60 cardholders)...")
    cardholders = generate_cardholders(num_cardholders=60, seed=42)
    print(f" -> Generated {len(cardholders)} cardholders.")

    print("[2/3] Generating 10,000 chronological transactions (T00001 - T10000)...")
    transactions = generate_transactions(cardholders, total_transactions=10000, seed=42)
    print(f" -> Generated {len(transactions)} transactions.")

    print(f"[3/3] Writing CSVs to {DATA_DIR}...")
    c_path, t_path = write_csvs(cardholders, transactions)
    print(f" -> Wrote cardholders to: {c_path}")
    print(f" -> Wrote transactions to: {t_path}")

    print("\n[Validation] Running rigorous schema and integrity audit...")
    report = validate_datasets(c_path, t_path)
    print(" -> Validation Audit: PASSED ✓")
    print(f"    Total Cardholders: {report['cardholders_count']}")
    print(f"    Total Transactions: {report['transactions_count']}")
    print(f"    Active Cards with History: {report['unique_cards_active']}")
    print(f"    Time Span: {report['time_span_start']} to {report['time_span_end']}")
    print(f"    High-Value / Suspicious Examples Detected: {report['suspicious_examples_detected']}")
    print("=" * 70)

if __name__ == "__main__":
    main()
