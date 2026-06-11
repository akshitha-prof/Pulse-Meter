"""Synthetic load generator for PulseMeter.

Generates random telemetry events and POSTs them in batches, then reports
measured throughput and the implied events/day. Use it to demonstrate that the
pipeline really sustains high volume.

Examples:
    python -m app.loadgen --n 200000 --batch 2000
    python -m app.loadgen --n 1000000 --batch 5000 --url http://localhost:8000
"""
import argparse
import random
import time

import httpx

SERVICES = ["search", "ads", "storage", "compute", "bigquery", "pubsub", "auth", "maps"]
REGIONS = ["us-central1", "europe-west1", "asia-south1", "asia-southeast1"]
EVENT_TYPES = ["request", "error", "throttle", "batch_job"]


def make_batch(size: int) -> dict:
    now = time.time()
    return {"events": [{
        "service": random.choice(SERVICES),
        "region": random.choice(REGIONS),
        "event_type": random.choices(EVENT_TYPES, weights=[80, 8, 5, 7])[0],
        "cost": round(random.uniform(0.0001, 0.05), 5),
        "units": random.randint(1, 500),
        "ts": now,
    } for _ in range(size)]}


def run(total: int, batch: int, url: str):
    sent = 0
    start = time.time()
    with httpx.Client(base_url=url, timeout=30.0) as client:
        while sent < total:
            size = min(batch, total - sent)
            r = client.post("/api/ingest", json=make_batch(size))
            r.raise_for_status()
            sent += size
            if sent % (batch * 20) == 0 or sent == total:
                elapsed = time.time() - start
                print(f"  sent {sent:,}/{total:,}  ({sent/elapsed:,.0f} ev/s)", end="\r")
    elapsed = time.time() - start
    rate = sent / elapsed
    print(f"\nSent {sent:,} events in {elapsed:.1f}s")
    print(f"Throughput: {rate:,.0f} events/sec  ->  ~{rate*86400/1_000_000:,.1f}M events/day")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=200_000, help="total events to send")
    p.add_argument("--batch", type=int, default=2000, help="events per request")
    p.add_argument("--url", default="http://localhost:8000")
    a = p.parse_args()
    run(a.n, a.batch, a.url)
