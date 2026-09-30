"""Генерирует транзакции в Kafka (topic: transactions). 1% fraud."""
import json, random, time, uuid
from datetime import datetime
from kafka import KafkaProducer
from faker import Faker

fake = Faker()
producer = KafkaProducer(
    bootstrap_servers="kafka:9092",
    value_serializer=lambda v: json.dumps(v).encode(),
    linger_ms=20, compression_type="lz4",
)

COUNTRIES = ["US", "DE", "FR", "RU", "BR", "IN", "CN"]
MERCHANTS = [f"M{i}" for i in range(1, 500)]
DEVICES = ["ios", "android", "web", "pos"]

def make_tx():
    fraud = random.random() < 0.01
    amount = round(random.uniform(5000, 50000), 2) if fraud else round(random.uniform(5, 500), 2)
    hour = datetime.utcnow().hour
    return {
        "tx_id": str(uuid.uuid4()),
        "user_id": random.randint(1, 50_000),
        "amount": amount,
        "currency": "USD",
        "merchant_id": random.choice(MERCHANTS),
        "merchant_category": random.choice(["grocery", "electronics", "travel", "crypto", "gambling"]),
        "device": random.choice(DEVICES),
        "country": random.choice(COUNTRIES),
        "ip_risk": round(random.uniform(0, 1) if fraud else random.uniform(0, 0.3), 3),
        "hour": hour,
        "ts": datetime.utcnow().isoformat(),
        "is_fraud": int(fraud),  # ground truth (для оффлайн-оценки)
    }

if __name__ == "__main__":
    print("🚀 simulator started")
    while True:
        for _ in range(200):
            producer.send("transactions", make_tx())
        producer.flush()
        time.sleep(0.5)
