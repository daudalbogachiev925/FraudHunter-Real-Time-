"""REST API: статистика, алерты, health."""
import os, json
from fastapi import FastAPI, Query
import psycopg
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="FraudHunter API", version="1.0.0")

def db(): return psycopg.connect(os.getenv("DB_URL"))

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/metrics")
def metrics(): return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/stats")
def stats():
    with db() as c, c.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*),
                   COUNT(*) FILTER (WHERE is_fraud=1),
                   AVG(probability),
                   MAX(scored_at)
            FROM scored
        """)
        total, frauds, avg_p, last = cur.fetchone()
    return {"total": total, "frauds": frauds, "avg_probability": float(avg_p or 0), "last_scored": last}

@app.get("/alerts")
def alerts(limit: int = Query(50, le=500), min_p: float = 0.6):
    with db() as c, c.cursor() as cur:
        cur.execute("""
            SELECT tx_id, user_id, amount, country, probability, scored_at
            FROM scored WHERE probability >= %s
            ORDER BY scored_at DESC LIMIT %s
        """, (min_p, limit))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

@app.get("/user/{user_id}")
def user(user_id: int):
    with db() as c, c.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*), AVG(probability), MAX(probability)
            FROM scored WHERE user_id=%s
        """, (user_id,))
        n, avg_p, max_p = cur.fetchone()
    return {"user_id": user_id, "tx_count": n,
            "avg_probability": float(avg_p or 0), "max_probability": float(max_p or 0)}
