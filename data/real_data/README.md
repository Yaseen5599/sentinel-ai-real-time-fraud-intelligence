# Sentinel AI — Synthetic Transaction & Cardholder Datasets

## Overview
This directory contains the synthetic 10,000-transaction financial intelligence evaluation dataset and customer cardholder registry for **Sentinel AI — Real-Time Financial Fraud Intelligence**.

> **CRITICAL COMPLIANCE NOTICE**:
> All records, customer names, card identifiers, locations, amounts, and transaction sequences are **100% synthetic**.
> They are generated programmatically for reproducibility, zero train-serve skew testing, and machine learning scoring verification.
> **No actual customer personal data, payment credentials, primary account numbers (PAN), CVVs, or live banking information are contained herein.**

---

## Dataset Inventory

### 1. `transactions_10000.csv`
- **Total Records**: 10,000 data rows (excluding CSV header).
- **Transaction ID Sequence**: `T00001` to `T10000` (strict 5-digit sequential format).
- **Chronological Span**: September 1, 2026 to October 9, 2026.
- **Attributes**:
  | Column Name | Type | Description |
  |---|---|---|
  | `transaction_id` | String | Unique identifier (`T00001` through `T10000`). |
  | `card_id` | String | Foreign key to `cardholders.csv` (`CARD_001` - `CARD_060`). |
  | `amount` | Numeric (2 dec) | Transaction currency amount (USD), positive numeric value. |
  | `merchant` | String | Merchant name matching project catalog (e.g. Amazon, Starbucks, Target, LuxuryJewelry). |
  | `location` | String | Transaction terminal city (e.g. New York, Chicago, San Francisco, London, Tokyo). |
  | `timestamp` | ISO 8601 String | UTC timestamp with timezone offset (`YYYY-MM-DDTHH:MM:SS+00:00`). |

### 2. `cardholders.csv`
- **Total Records**: 60 unique customer profiles.
- **Key Relationships**: 100% of transactions in `transactions_10000.csv` map to an active cardholder.
- **Attributes**:
  | Column Name | Type | Description |
  |---|---|---|
  | `card_id` | String (PK) | Unique card identifier (`CARD_001` through `CARD_060`). |
  | `customer_id` | String | Synthetic unique customer ID (`CUST_001` through `CUST_060`). |
  | `customer_name` | String | Synthetic customer full name. |
  | `account_age_days` | Integer | Account tenure in days (90 to 1800 days). |
  | `usual_transaction_amount`| Numeric (2 dec) | Historical average spend baseline for this cardholder. |
  | `usual_transaction_frequency` | Numeric | Mean daily transaction velocity baseline. |
  | `usual_active_hours` | String | Typical diurnal spending window (e.g. `07:00-22:00`). |
  | `home_location` | String | Primary domestic billing and residence city. |
  | `created_at` | ISO 8601 String | Customer account creation timestamp. |

---

## Reproducibility & Pipeline Scripts

### Regenerate Datasets
To regenerate both CSVs from scratch using the deterministic random seed (`seed=42`):
```bash
python scripts/generate_real_data_csvs.py
```

### Validate Datasets
To execute the automated validation audit checking row counts, sequential IDs, foreign-key integrity, non-null constraints, and timestamp monotonicity:
```bash
python scripts/validate_datasets.py
```

---

## Model Compatibility & Zero Train-Serve Skew
- **Active Model**: `models/canonical_random_forest.pkl` (`canonical-rf-v1.0`).
- **Feature Pipeline**: The 18 canonical observable features are derived dynamically via `src.features.canonical_features.CanonicalFeatureExtractor`.
- **Zero Future Data Leakage**: In the transaction risk analysis search engine, historical cardholder transactions are strictly filtered to those occurring **before** the evaluated transaction's timestamp.
