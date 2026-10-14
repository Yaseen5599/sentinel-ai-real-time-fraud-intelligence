# Sentinel AI — Real-Time Adaptive Fraud Intelligence System

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-3.7.0-black.svg?logo=apachekafka)](https://kafka.apache.org/)
[![Apache Spark](https://img.shields.io/badge/Apache_Spark-4.2.0-orange.svg?logo=apachespark)](https://spark.apache.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black.svg?logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker)](https://www.docker.com/)

**Sentinel AI** is an enterprise-grade, big-data financial fraud detection and intelligence platform. It fuses distributed batch processing, sub-second real-time streaming, personalized cardholder behavioral baselining, supervised machine learning, unsupervised anomaly detection, and deterministic rule engines with human-explainable alerts and an interactive investigation dashboard.

---

## Architecture Overview

```text
               +------------------------------------------+
               | Synthetic / Real Transaction Producer    |
               +------------------------------------------+
                                    |
                                    v
               +------------------------------------------+
               |     Apache Kafka Message Broker          |
               |     Topic: `transactions-canonical`      |
               +------------------------------------------+
                                    |
         +--------------------------+--------------------------+
         |                                                     |
         v                                                     v
+------------------------------------+   +------------------------------------+
|  PySpark Structured Streaming      |   |   FastAPI REST Backend             |
|  - Temporal Windows (1m, 10m, 24h) |   |   - Authenticated JWT Endpoints    |
|  - Causal Behavioral Profiling     |   |   - Real-time Analytics & KPIs     |
|  - Hybrid Risk Scoring Engine      |   |   - Investigation Audit Workflows  |
+------------------------------------+   +------------------------------------+
         |                                                     |
         +--------------------------+--------------------------+
                                    |
                                    v
               +------------------------------------------+
               |   PostgreSQL / Supabase Storage Layer    |
               |   - Row-Level Security (RLS)             |
               |   - Partitioned Event Store & Outbox     |
               +------------------------------------------+
                                    |
                                    v
               +------------------------------------------+
               |     Next.js 14 Web Command Center        |
               |     - Real-Time Live Stream Feed         |
               |     - Investigator Review & Feedback     |
               |     - Sub-Second Latency Monitoring      |
               +------------------------------------------+
```

---

## Core Features

1. **Adaptive Hybrid Scoring Engine:**
   Combines three complementary detection mechanisms into a unified composite risk score:
   $$\text{Final Score} = 0.50 \times \text{ML Probability} + 0.30 \times \text{Behavioral Anomaly} + 0.20 \times \text{Rule Penalty}$$
2. **Personalized Behavioral Profiling:**
   Evaluates transactions against each cardholder's historical baseline across strict causal 1-minute, 10-minute, and 24-hour windows (burst velocity, spending deviation, active operating hours).
3. **Deterministic Business Fraud Rules:**
   Enforces 7 explicit banking domain rules (burst transactions, impossible geographical travel, unseen high-value merchants, declined-to-success swarms, etc.) with auditable explanations.
4. **Sub-Second Streaming Latency:**
   Average end-to-end detection latency under ~15 ms per transaction using PySpark Structured Streaming and Apache Kafka.
5. **Modern Security & Investigation Workflow:**
   FastAPI service protected by Supabase JWT authentication, PostgreSQL Row-Level Security (RLS), and audit logs for investigator case resolution.
6. **Next.js 14 Command Center:**
   Live dashboard with real-time telemetry, transaction inspector, KPIs, and investigator decision tools.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Streaming & Ingestion** | Apache Kafka 3.7.0, PySpark 4.2.0 Structured Streaming |
| **Machine Learning** | Scikit-learn (Random Forest, Logistic Regression, Isolation Forest) |
| **Backend API** | Python 3.11+, FastAPI, Pydantic, SQLAlchemy, Uvicorn |
| **Frontend Dashboard** | Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide Icons |
| **Database & Security** | PostgreSQL 15 / Supabase, Row-Level Security (RLS), JWT (HS256) |
| **Containerization** | Docker, Multi-stage Dockerfiles (`Dockerfile.api`, `Dockerfile.spark`, `Dockerfile.web`), Docker Compose |

---

## Dataset & Model Benchmarks

The offline training pipeline utilizes the public **Credit Card Fraud Detection** benchmark (ULB / Kaggle):
* **Transactions:** 284,807 across 48 hours
* **Fraud Rate:** 492 cases (0.173% — extreme class imbalance)
* **Chronological Split:** Strict 80/20 train/test split at `Time = 145,247.0s` (56,962 test transactions) to eliminate temporal data leakage.

### Offline Evaluation Metrics

| Model | Precision | Recall | F1-Score | PR-AUC | FP per 1000 txns | Total Cost ($)* |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Baseline)** | 0.0441 | **0.9067** | 0.0842 | 0.7622 | 25.86 | $25,595.00 |
| **Random Forest (Primary)** | **0.9194** | 0.7600 | **0.8321** | **0.8150** | **0.09** | **$9,075.00** |
| **Isolation Forest (Anomaly)** | 0.0000 | 0.0000 | 0.0000 | 0.0319 | 1.69 | $38,940.00 |

*\*Cost Function: `Total Cost = C_FN * FN + C_FP * FP` ($500 per missed fraud, $15 per false positive).*

---

## Project Structure

```text
.
├── config/                     # Pipeline configurations, risk weights, thresholds
├── data/
│   ├── raw/                    # Raw dataset location (.gitkeep)
│   ├── processed/              # Distributed Spark output location (.gitkeep)
│   └── synthetic/              # Sample streaming transaction events
├── docker-compose.yml          # Core infrastructure (Kafka + Postgres)
├── docker-compose.prod.yml     # Full-stack production multi-container setup
├── Dockerfile.api              # FastAPI container definition
├── Dockerfile.spark            # PySpark streaming container definition
├── Dockerfile.web              # Next.js web dashboard container definition
├── jars/                       # Spark Kafka connector JAR dependencies
├── models/                     # Pre-trained ML models, scalers, and metadata
├── notebooks/                  # Phase 1-8 Jupyter research & validation notebooks
├── scripts/                    # Helper scripts and data generation utilities
├── sql/                        # Database DDL schema and RLS migrations
├── src/
│   ├── api/                    # FastAPI backend endpoints and auth dependencies
│   ├── database/               # PostgreSQL client and queries
│   ├── features/               # Behavioral profiling and temporal windowing
│   ├── models/                 # Model training, inference, and hybrid scoring
│   ├── producer/               # Kafka transaction simulator
│   ├── rules/                  # 7 deterministic business fraud rules
│   └── streaming/              # Spark batch and structured streaming runners
├── tests/                      # Automated pytest unit, scenario, and security suites
├── web/                        # Next.js 14 TypeScript web frontend
├── .env.example                # Safe environment configuration template
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## Getting Started

### 1. Prerequisites
* **Docker & Docker Compose** (Docker Desktop recommended)
* **Python 3.11+**
* **Node.js 18+** & **npm**
* **Java OpenJDK 17+** (Required if running Spark locally outside Docker)

### 2. Clone and Configure Environment

```bash
# Clone the repository
git clone https://github.com/Yaseen5599/sentinel-ai-real-time-fraud-intelligence.git
cd sentinel-ai-real-time-fraud-intelligence

# Copy environment template
cp .env.example .env
```

Edit `.env` to configure your settings (or use standard local development defaults).

### 3. Download the Kaggle Dataset (Optional for Retraining)

To train models from scratch or run batch Spark jobs:
1. Download `creditcard.csv` from [Kaggle Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud).
2. Place the file in the `data/raw/` folder:
   ```bash
   ls data/raw/creditcard.csv
   ```
*(Pre-trained model artifacts are already included in `models/`, allowing you to run streaming and API services immediately without re-downloading the full dataset).*

---

## Running with Docker (Recommended)

### Option A: Local Dev Infrastructure (Kafka + PostgreSQL)
```bash
# Start Kafka and PostgreSQL
docker compose up -d

# Verify containers are healthy
docker compose ps
```

### Option B: Full-Stack Production Deployment
To spin up all services (Kafka, PostgreSQL, FastAPI Backend, Spark Streaming Worker, and Next.js Web):
```bash
docker compose -f docker-compose.prod.yml up --build -d
```
Access the services:
* **Web Dashboard:** `http://localhost:3000`
* **FastAPI Docs:** `http://localhost:8000/docs`
* **Kafka Broker:** `localhost:9092`
* **PostgreSQL:** `localhost:5433`

---

## Running Locally for Development

### 1. Backend & Streaming Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-api.txt
```

### 2. Start Services
In separate terminal tabs:

* **Tab 1 — Start Infrastructure:**
  ```bash
  docker compose up -d
  ```

* **Tab 2 — Start FastAPI Backend:**
  ```bash
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
  ```

* **Tab 3 — Start Spark Streaming Worker:**
  ```bash
  python src/streaming/spark_streaming_pipeline.py
  ```

* **Tab 4 — Publish Streaming Transactions:**
  ```bash
  # Publish 100 transactions at 0.1s intervals
  python src/producer/kafka_producer.py 100 0.1
  ```

* **Tab 5 — Start Next.js Frontend:**
  ```bash
  cd web
  npm install
  npm run dev
  ```
  Open `http://localhost:3000` in your browser.

---

## Running Tests

Execute the automated test suite across unit, scenario, and security validations:
```bash
pytest tests/ -v
```

---

## Security & Compliance

* **Environment Isolation:** Secrets and keys are loaded strictly from environment variables and must never be committed to source control.
* **Row-Level Security (RLS):** Database queries are isolated by user role (`customer`, `fraud_investigator`, `admin`).
* **Safe Placeholders:** All repository configuration templates use explicit sanitization tokens (`[YOUR-PASSWORD]`, `[YOUR-PROJECT-REF]`).

---

## License

This project is licensed under the Apache 2.0 License.
