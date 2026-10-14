"""
Sentinel AI — Canonical Transaction Stream Generator
Simulates realistic financial transactions conforming to the Canonical Transaction Schema.
Generates baseline cardholder spending and concrete fraud attack vectors
(account takeover, velocity bursts, impossible travel, high-value spikes, card testing).
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

CITY_COORDINATES = {
    "New York": {"country": "US", "lat": 40.7128, "lon": -74.0060},
    "Chicago": {"country": "US", "lat": 41.8781, "lon": -87.6298},
    "San Francisco": {"country": "US", "lat": 37.7749, "lon": -122.4194},
    "Seattle": {"country": "US", "lat": 47.6062, "lon": -122.3321},
    "Boston": {"country": "US", "lat": 42.3601, "lon": -71.0589},
    "London": {"country": "GB", "lat": 51.5074, "lon": -0.1278},
    "Tokyo": {"country": "JP", "lat": 35.6762, "lon": 139.6503},
    "Singapore": {"country": "SG", "lat": 1.3521, "lon": 103.8198},
    "Paris": {"country": "FR", "lat": 48.8566, "lon": 2.3522},
    "Sydney": {"country": "AU", "lat": -33.8688, "lon": 151.2093},
    "Mumbai": {"country": "IN", "lat": 19.0760, "lon": 72.8777},
}

MERCHANT_CATALOG = {
    "Amazon": {"mcc": "5311", "category": "Department Store", "channel": "ONLINE_ECOMMERCE"},
    "Starbucks": {"mcc": "5814", "category": "Fast Food", "channel": "IN_PERSON_CONTACTLESS"},
    "Target": {"mcc": "5311", "category": "Retail", "channel": "IN_PERSON_CHIP"},
    "Walmart": {"mcc": "5411", "category": "Grocery", "channel": "IN_PERSON_CHIP"},
    "WholeFoods": {"mcc": "5411", "category": "Grocery", "channel": "IN_PERSON_CONTACTLESS"},
    "Uber": {"mcc": "4121", "category": "Transportation", "channel": "ONLINE_ECOMMERCE"},
    "ShellGas": {"mcc": "5541", "category": "Service Station", "channel": "IN_PERSON_CHIP"},
    "CVSPharmacy": {"mcc": "5411", "category": "Pharmacy", "channel": "IN_PERSON_CHIP"},
    "OnlineStore": {"mcc": "5311", "category": "E-Commerce", "channel": "ONLINE_ECOMMERCE"},
    "LuxuryJewelry": {"mcc": "5944", "category": "Jewelry", "channel": "ONLINE_ECOMMERCE"},
    "CryptoExchange": {"mcc": "6051", "category": "Quasi Cash / Crypto", "channel": "ONLINE_ECOMMERCE"},
    "HighEndElectronics": {"mcc": "5732", "category": "Consumer Electronics", "channel": "ONLINE_ECOMMERCE"},
    "OverseasCasino": {"mcc": "7995", "category": "Betting / Casino", "channel": "ONLINE_ECOMMERCE"},
}

CARDHOLDERS = {
    f"CARD_{i:03d}": {
        "account_id": f"ACC_{i:03d}",
        "customer_name": f"Customer {i:03d}",
        "base_amount": round(random.uniform(25.0, 120.0), 2),
        "home_location": random.choice(["New York", "Chicago", "San Francisco", "Seattle", "Boston"]),
        "frequent_merchants": random.sample(
            ["Amazon", "Starbucks", "Target", "Walmart", "WholeFoods", "Uber", "ShellGas", "CVSPharmacy"],
            k=3
        ),
        "active_hours": list(range(7, 23))
    }
    for i in range(1, 31)
}

class TransactionGenerator:
    """
    Generates realistic canonical transactions and simulates structured fraud attacks.
    """

    def __init__(self, seed: Optional[int] = 42):
        if seed:
            random.seed(seed)
        self.tx_counter = 10000
        self.profiles = CARDHOLDERS

    def _build_canonical_payload(self,
                                 txn_id: str,
                                 card_id: str,
                                 amount: float,
                                 merchant_name: str,
                                 city: str,
                                 timestamp: datetime,
                                 status: str = "SUCCESS",
                                 channel: Optional[str] = None,
                                 scenario: str = "NORMAL_SPEND") -> Dict[str, Any]:
        """Assembles a canonical schema compliant transaction dictionary."""
        loc_meta = CITY_COORDINATES.get(city, CITY_COORDINATES["New York"])
        merch_meta = MERCHANT_CATALOG.get(merchant_name, {"mcc": "5411", "channel": "ONLINE_ECOMMERCE"})

        idemp_key = f"IDEMP_{uuid.uuid4().hex[:16]}"
        chan = channel or merch_meta.get("channel", "ONLINE_ECOMMERCE")
        account_id = self.profiles.get(card_id, {}).get("account_id", f"ACC_{card_id[-3:]}")

        iso_ts = timestamp.astimezone(timezone.utc).isoformat() if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc).isoformat()

        return {
            "transaction_id": txn_id,
            "idempotency_key": idemp_key,
            "card_id": card_id,
            "account_id": account_id,
            "amount": round(float(amount), 2),
            "currency": "USD",
            "channel": chan,
            "merchant_id": f"MERCH_{merchant_name.upper()[:12]}",
            "merchant_name": merchant_name,
            "merchant_category_code": merch_meta["mcc"],
            "city": city,
            "country": loc_meta["country"],
            "latitude": loc_meta["lat"],
            "longitude": loc_meta["lon"],
            "location": city,  # Legacy field compatibility
            "merchant": merchant_name,  # Legacy field compatibility
            "device_fingerprint": f"DEV_{hash((card_id, city)) & 0xFFFFFF:06x}",
            "authorization_status": "AUTHORIZED" if status == "SUCCESS" else "DECLINED",
            "status": status,
            "timestamp": iso_ts,
            "scenario": scenario
        }

    def generate_normal_transaction(self, card_id: Optional[str] = None, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate regular, legitimate transaction fitting customer profile."""
        self.tx_counter += 1
        if not card_id or card_id not in self.profiles:
            card_id = random.choice(list(self.profiles.keys()))

        profile = self.profiles[card_id]
        if timestamp is None:
            now = datetime.now(timezone.utc)
            hour = random.choice(profile["active_hours"])
            timestamp = now.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59), microsecond=0)

        amount = round(max(3.50, random.gauss(profile["base_amount"], profile["base_amount"] * 0.3)), 2)
        merchant = random.choice(profile["frequent_merchants"])
        city = profile["home_location"]

        return self._build_canonical_payload(
            txn_id=f"TX{self.tx_counter}",
            card_id=card_id,
            amount=amount,
            merchant_name=merchant,
            city=city,
            timestamp=timestamp,
            status="SUCCESS",
            scenario="NORMAL_SPEND"
        )

    def generate_scenario_rapid_burst(self, card_id: str = "CARD_007", count: int = 7) -> List[Dict[str, Any]]:
        """Scenario: Rapid transactions (>5 txns within 2 minutes)."""
        txns = []
        base_time = datetime.now(timezone.utc)
        city = self.profiles.get(card_id, {}).get("home_location", "Chicago")
        for i in range(count):
            self.tx_counter += 1
            t_time = base_time + timedelta(seconds=i * 12)
            txns.append(self._build_canonical_payload(
                txn_id=f"TX{self.tx_counter}",
                card_id=card_id,
                amount=round(random.uniform(40.0, 95.0), 2),
                merchant_name="OnlineStore",
                city=city,
                timestamp=t_time,
                status="SUCCESS",
                scenario="RAPID_TRANSACTION_BURST"
            ))
        return txns

    def generate_scenario_impossible_travel(self, card_id: str = "CARD_012") -> List[Dict[str, Any]]:
        """Scenario: Two transactions from geographically distant locations within a short period."""
        self.tx_counter += 1
        t1 = datetime.now(timezone.utc) - timedelta(minutes=15)
        first_txn = self._build_canonical_payload(
            txn_id=f"TX{self.tx_counter}",
            card_id=card_id,
            amount=35.50,
            merchant_name="Starbucks",
            city="New York",
            timestamp=t1,
            status="SUCCESS",
            scenario="NORMAL_SPEND"
        )

        self.tx_counter += 1
        t2 = datetime.now(timezone.utc)
        second_txn = self._build_canonical_payload(
            txn_id=f"TX{self.tx_counter}",
            card_id=card_id,
            amount=420.00,
            merchant_name="LuxuryJewelry",
            city="Singapore",  # 15 minutes later in Singapore (9,500+ miles away)
            timestamp=t2,
            status="SUCCESS",
            scenario="IMPOSSIBLE_TRAVEL"
        )
        return [first_txn, second_txn]

    def generate_scenario_high_value_spike(self, card_id: str = "CARD_005") -> Dict[str, Any]:
        """Scenario: High-value abnormal transaction significantly above customer normal spending (>6x)."""
        self.tx_counter += 1
        normal_base = self.profiles.get(card_id, {}).get("base_amount", 60.0)
        city = self.profiles.get(card_id, {}).get("home_location", "San Francisco")
        spike_amount = round(normal_base * 6.5, 2)

        return self._build_canonical_payload(
            txn_id=f"TX{self.tx_counter}",
            card_id=card_id,
            amount=spike_amount,
            merchant_name="CryptoExchange",
            city=city,
            timestamp=datetime.now(timezone.utc),
            status="SUCCESS",
            scenario="HIGH_VALUE_ABNORMAL_SPIKE"
        )

    def generate_scenario_account_takeover(self, card_id: str = "CARD_018") -> Dict[str, Any]:
        """Scenario: Account takeover (3 AM, overseas casino, high amount)."""
        self.tx_counter += 1
        now = datetime.now(timezone.utc).replace(hour=3, minute=18, second=42, microsecond=0)
        normal_base = self.profiles.get(card_id, {}).get("base_amount", 70.0)

        return self._build_canonical_payload(
            txn_id=f"TX{self.tx_counter}",
            card_id=card_id,
            amount=round(normal_base * 5.2, 2),
            merchant_name="OverseasCasino",
            city="Tokyo",
            timestamp=now,
            status="SUCCESS",
            scenario="ACCOUNT_TAKEOVER"
        )

    def generate_scenario_declined_card_testing(self, card_id: str = "CARD_022") -> List[Dict[str, Any]]:
        """Scenario: Multiple declined transactions followed by a high-value successful transaction."""
        txns = []
        base_time = datetime.now(timezone.utc) - timedelta(minutes=6)
        for i in range(2):
            self.tx_counter += 1
            t_time = base_time + timedelta(minutes=i * 2)
            txns.append(self._build_canonical_payload(
                txn_id=f"TX{self.tx_counter}",
                card_id=card_id,
                amount=round(random.uniform(5.0, 15.0), 2),
                merchant_name="HighEndElectronics",
                city="London",
                timestamp=t_time,
                status="DECLINED",
                scenario="CARD_TESTING_DECLINED"
            ))

        self.tx_counter += 1
        txns.append(self._build_canonical_payload(
            txn_id=f"TX{self.tx_counter}",
            card_id=card_id,
            amount=1450.00,
            merchant_name="HighEndElectronics",
            city="London",
            timestamp=datetime.now(timezone.utc),
            status="SUCCESS",
            scenario="DECLINED_FOLLOWED_BY_SUCCESS"
        ))
        return txns
