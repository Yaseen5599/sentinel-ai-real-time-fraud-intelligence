"""
End-to-End Scenario Testing
Tests synthetic suspicious and fraudulent transaction scenarios through the pipeline
and verifies that fraud alerts and explainable reasons reach PostgreSQL.
"""

from datetime import datetime, timedelta
from src.streaming.spark_streaming_pipeline import RealTimeStreamProcessor
from src.producer.transaction_generator import TransactionGenerator
from src.database.db_client import DatabaseClient

def test_streaming_fraud_scenarios():
    processor = RealTimeStreamProcessor()
    gen = TransactionGenerator()
    db = DatabaseClient()

    # Step 1: Establish history for CARD_999 (Normal customer profile)
    card_id = "CARD_999"
    t0 = datetime.now() - timedelta(hours=5)
    print(f"[Scenario Test] Establishing 10 normal transactions for {card_id}...")
    for i in range(10):
        t_hist = {
            "transaction_id": f"TX_NORM_{i}",
            "card_id": card_id,
            "amount": 50.0 + (i * 2.0),
            "merchant": "Target",
            "location": "New York",
            "timestamp": (t0 + timedelta(minutes=i * 20)).isoformat(),
            "status": "SUCCESS"
        }
        res = processor.process_transaction(t_hist)
        assert res["fraud_decision"] == "LEGITIMATE"

    # Step 2: Trigger Impossible Travel + Amount Spike (FRAUD scenario)
    print("\n[Scenario Test] Triggering Impossible Travel + 8x Amount Spike...")
    fraud_txn = {
        "transaction_id": "TX_FRAUD_TRAVEL_01",
        "card_id": card_id,
        "amount": 750.00,  # >10x normal $50-$70
        "merchant": "LuxuryJewelry",
        "location": "Singapore",  # 10 minutes later in Singapore!
        "timestamp": (datetime.now()).isoformat(),
        "status": "SUCCESS",
        "scenario": "IMPOSSIBLE_TRAVEL"
    }
    fraud_res = processor.process_transaction(fraud_txn)
    print(f" -> Decision: {fraud_res['fraud_decision']} | Score: {fraud_res['final_fraud_score']}")
    print(f" -> Explanation: {fraud_res['explanation']}")
    assert fraud_res["fraud_decision"] in ["SUSPICIOUS", "FRAUD"]
    assert "Impossible travel" in fraud_res["explanation"] or "Amount" in fraud_res["explanation"]

    # Step 3: Trigger Rapid Velocity Burst (>5 txns in 2 minutes)
    burst_card = "CARD_888"
    print("\n[Scenario Test] Triggering Rapid Velocity Burst on CARD_888...")
    now = datetime.now()
    burst_results = []
    for i in range(7):
        burst_txn = {
            "transaction_id": f"TX_BURST_{i}",
            "card_id": burst_card,
            "amount": 80.0,
            "merchant": "OnlineStore",
            "location": "Chicago",
            "timestamp": (now + timedelta(seconds=i * 10)).isoformat(),
            "status": "SUCCESS",
            "scenario": "RAPID_TRANSACTION_BURST"
        }
        b_res = processor.process_transaction(burst_txn)
        burst_results.append(b_res)

    last_burst = burst_results[-1]
    print(f" -> Last Burst Decision: {last_burst['fraud_decision']} | Score: {last_burst['final_fraud_score']}")
    print(f" -> Explanation: {last_burst['explanation']}")
    assert last_burst["fraud_decision"] in ["SUSPICIOUS", "FRAUD"]

    # Step 4: Verify in PostgreSQL
    kpis = db.get_kpis()
    print(f"\n[PostgreSQL Verification] Total: {kpis['total_transactions']}, Fraud/Suspicious: {kpis['fraud_transactions']}, Rate: {kpis['fraud_rate_pct']}%")
    assert kpis["fraud_transactions"] > 0

    recent_flagged = db.get_recent_transactions(limit=5, flagged_only=True)
    print(f"[Flagged Transactions in DB]: {len(recent_flagged)} found.")
    for f in recent_flagged:
        print(f" -> ID: {f['transaction_id']} | Card: {f['card_id']} | {f['fraud_decision']} | {f['explanation'][:80]}...")

    print("\n[SUCCESS] End-to-end scenario testing validated successfully!")

if __name__ == "__main__":
    test_streaming_fraud_scenarios()
