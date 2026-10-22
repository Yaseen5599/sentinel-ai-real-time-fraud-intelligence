#!/usr/bin/env python3
"""
Sentinel AI — Dataset Validation Audit Script
Validates data/real_data/cardholders.csv and data/real_data/transactions_10000.csv.
Exits with 0 on pass, 1 on validation error.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_real_data_csvs import validate_datasets, CARDHOLDERS_CSV, TRANSACTIONS_CSV

def main():
    print("=" * 60)
    print("Sentinel AI — Real-Data CSV Validation Suite")
    print(f"Cardholders: {CARDHOLDERS_CSV}")
    print(f"Transactions: {TRANSACTIONS_CSV}")
    print("=" * 60)
    try:
        report = validate_datasets(CARDHOLDERS_CSV, TRANSACTIONS_CSV)
        print("✓ All validation criteria PASSED successfully.")
        print(f"  • Cardholders: {report['cardholders_count']}")
        print(f"  • Transactions: {report['transactions_count']}")
        print(f"  • Active Cards: {report['unique_cards_active']}")
        print(f"  • Time Horizon: {report['time_span_start']} -> {report['time_span_end']}")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"✗ Validation FAILED: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
