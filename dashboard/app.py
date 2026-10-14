"""
Streamlit Real-Time Credit Card Fraud Detection Dashboard
Visualizes live transaction throughput, fraud alert rates, risk distributions,
top suspicious cardholders, and explainable alert details.
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from src.database.db_client import DatabaseClient

# Page configuration
st.set_page_config(
    page_title="FraudShield | Real-Time Credit Card Fraud Analytics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #FFFFFF;
        padding: 1.2rem;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 5px solid #3B82F6;
    }
    .badge-fraud {
        background-color: #EF4444;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-suspicious {
        background-color: #F59E0B;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-legit {
        background-color: #10B981;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DB client
@st.cache_resource
def get_db():
    return DatabaseClient()

db = get_db()

# Sidebar controls
st.sidebar.image("https://img.icons8.com/color/96/000000/shield.png", width=64)
st.sidebar.title("Adaptive Fraud Shield")
st.sidebar.caption("Kafka + Spark + Behavioral Analytics")

auto_refresh = st.sidebar.checkbox("Live Auto-Refresh (2s)", value=True)
refresh_interval = 2

st.sidebar.markdown("---")
st.sidebar.subheader("System Architecture")
st.sidebar.info("""
**1. Stream Generation:** Kafka Producer  
**2. Real-Time Analytics:** Spark Streaming  
**3. Scoring Engine:**  
   - 0.5 × ML Model  
   - 0.3 × Behavioral Baseline  
   - 0.2 × Deterministic Rules  
**4. Persistent Store:** PostgreSQL  
""")

# Main Title
st.markdown('<div class="main-header">🛡️ Real-Time Credit Card Fraud Detection</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Adaptive stream monitoring using Apache Kafka, Spark Structured Streaming & Personalized Behavioral Baselines</div>', unsafe_allow_html=True)

# Fetch KPIs
kpis = db.get_kpis()
total_txns = kpis["total_transactions"]
fraud_txns = kpis["fraud_transactions"]
fraud_rate = kpis["fraud_rate_pct"]
avg_latency = kpis["avg_latency_ms"]

# Display KPI Row
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Total Transactions", f"{total_txns:,}")
with kpi2:
    st.metric("Suspected / Fraud", f"{fraud_txns:,}", delta=f"{fraud_rate}% rate", delta_color="inverse")
with kpi3:
    st.metric("Fraud Alert Rate", f"{fraud_rate:.2f}%")
with kpi4:
    st.metric("Avg Latency", f"{avg_latency:.2f} ms")

st.markdown("---")

# Layout: 2 Columns for Charts
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🚩 Fraud Alerts by Merchant")
    merchant_data = db.get_fraud_by_merchant(limit=8)
    if merchant_data:
        m_df = pd.DataFrame(merchant_data)
        st.bar_chart(m_df.set_index("merchant")["fraud_count"], color="#EF4444")
    else:
        st.info("No merchant fraud alerts recorded yet.")

with col_right:
    st.subheader("🌍 Fraud Alerts by Location")
    location_data = db.get_fraud_by_location(limit=8)
    if location_data:
        l_df = pd.DataFrame(location_data)
        st.bar_chart(l_df.set_index("location")["fraud_count"], color="#F59E0B")
    else:
        st.info("No location fraud alerts recorded yet.")

# Top Suspicious Cards & Risk Score Distribution
col_card, col_dist = st.columns([1, 1])

with col_card:
    st.subheader("💳 Top Suspicious Cardholders")
    top_cards = db.get_top_suspicious_cards(limit=5)
    if top_cards:
        c_df = pd.DataFrame(top_cards)
        st.dataframe(c_df, use_container_width=True)
    else:
        st.info("No cards currently exceeding risk thresholds.")

with col_dist:
    st.subheader("📊 Risk Score Distribution")
    scores = db.get_score_distribution()
    if scores:
        chart_data = pd.DataFrame({"Score": scores})
        st.line_chart(chart_data)
    else:
        st.info("Awaiting scored transactions.")

st.markdown("---")

# Flagged and Recent Transactions
st.subheader("⚡ Live Transaction Feed & Explainable Alerts")
tab1, tab2 = st.tabs(["🚨 Flagged Incidents (Suspicious / Fraud)", "📋 All Recent Transactions"])

with tab1:
    flagged = db.get_recent_transactions(limit=25, flagged_only=True)
    if flagged:
        for txn in flagged:
            decision_color = "red" if txn["fraud_decision"] == "FRAUD" else "orange"
            with st.expander(f"⚠️ {txn['transaction_id']} | Card: {txn['card_id']} | Amount: ${txn['amount']} | Decision: {txn['fraud_decision']} (Score: {txn['final_fraud_score']:.2f})"):
                st.markdown(f"**Merchant:** `{txn['merchant']}` | **Location:** `{txn['location']}` | **Timestamp:** `{txn['timestamp']}`")
                st.markdown(f"**Score Breakdown:** ML Model: `{txn['ml_score']:.2f}` | Behavior: `{txn['behavior_score']:.2f}` | Rules: `{txn['rule_score']:.2f}`")
                st.warning(f"**Triggered Explanation:**\n{txn['explanation']}")
    else:
        st.success("No suspicious transactions currently flagged.")

with tab2:
    recent = db.get_recent_transactions(limit=30, flagged_only=False)
    if recent:
        r_df = pd.DataFrame(recent)
        display_cols = ["transaction_id", "card_id", "amount", "merchant", "location", "timestamp", "final_fraud_score", "fraud_decision", "explanation"]
        st.dataframe(r_df[display_cols], use_container_width=True)
    else:
        st.info("No transactions logged yet.")

# Auto refresh logic
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
