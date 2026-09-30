"""Читает Kafka, скорит XGBoost, публикует alerts, пишет в Postgres."""
import os, json, time, logging, hashlib
from datetime import datetime
import numpy as np, pandas as pd
import xgboost as xgb
from kafka import KafkaConsumer, KafkaProducer
import mlflow.xgboost
import redis, psycopg
from prometheus_client import Counter, Histogram, start_http_server

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("stream")

SCORED = Counter("fh_scored_total", "Scored transactions")
FRAUDS = Counter("fh_frauds_total", "Flagged frauds")
LAT = Histogram("fh_score_latency_seconds", "Score latency")

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
MODEL_URI = os.getenv("MODEL_URI", "models:/fraud-xgb/Production")

log.info("Loading %s", MODEL_URI)
model = mlflow.xgboost.load_model(MODEL_URI)
THRESHOLD = 0.6

cache = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)

conn = psycopg.connect(os.getenv("DB_URL"))
with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scored (
            tx_id TEXT PRIMARY KEY,
            user_id BIGINT, amount FLOAT, country TEXT, merchant_id TEXT,
            probability FLOAT, is_fraud INT, scored_at TIMESTAMP DEFAULT NOW()
        )""")
conn.commit()

consumer = KafkaConsumer(
    "transactions", bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
    value_deserializer=lambda v: json.loads(v.decode()),
    auto_offset_reset="latest", enable_auto_commit=True,
    group_id="fh-scorer", max_poll_records=500,
)
producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
    value_serializer=lambda v: json.dumps(v).encode(),
)

FEATURES = ["amount", "ip_risk", "merchant_cat", "device", "country", "hour"]
CAT_MAP = {"grocery": 0, "electronics": 1, "travel": 2, "crypto": 3, "gambling": 4}
DEV_MAP = {"ios": 0, "android": 1, "web": 2, "pos": 3}
CTRY_MAP = {"US": 0, "DE": 1, "FR": 2, "RU": 3, "BR": 4, "IN": 5, "CN": 6}

def featurize(tx):
    return {
        "amount": tx["amount"],
        "ip_risk": tx["ip_risk"],
        "merchant_cat": CAT_MAP.get(tx["merchant_category"], 0),
        "device": DEV_MAP.get(tx["device"], 0),
        "country": CTRY_MAP.get(tx["country"], 0),
        "hour": tx["hour"],
    }

def score(batch):
    X = pd.DataFrame([featurize(t) for t in batch])[FEATURES]
    dmat = xgb.DMatrix(X)
    booster = model.get_booster()
    return booster.predict(dmat)

def main():
    start_http_server(9100)
    log.info("consumer started")
    buffer = []
    while True:
        for msg in consumer:
            buffer.append(msg.value)
            if len(buffer) >= 200:
                with LAT.time():
                    probs = score(buffer)
                SCORED.inc(len(buffer))
                rows = []
                for tx, p in zip(buffer, probs):
                    fraud = int(p >= THRESHOLD)
                    if fraud:
                        FRAUDS.inc()
                        producer.send("alerts", {
                            "tx_id": tx["tx_id"], "user_id": tx["user_id"],
                            "amount": tx["amount"], "probability": float(p),
                            "country": tx["country"], "ts": tx["ts"],
                        })
                    rows.append((tx["tx_id"], tx["user_id"], tx["amount"],
                                 tx["country"], tx["merchant_id"], float(p), fraud))
                with conn.cursor() as cur:
                    cur.executemany("""
                        INSERT INTO scored (tx_id,user_id,amount,country,merchant_id,probability,is_fraud)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (tx_id) DO NOTHING""", rows)
                conn.commit()
                buffer = []
        time.sleep(0.1)

if __name__ == "__main__":
    main()
