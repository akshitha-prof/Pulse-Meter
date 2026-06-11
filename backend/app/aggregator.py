"""In-memory streaming aggregator for telemetry events.

Designed for high ingest throughput: events fold into rolling counters under a
single lock instead of being stored row-by-row. This is what lets a modest box
absorb millions of events/day. A per-minute bucket map powers the time series,
and a short deque of recent (timestamp, count) samples powers the live rate.

In production you'd flush these rollups to a columnar store (BigQuery/ClickHouse)
on an interval — the aggregation shape here maps directly onto a `GROUP BY`.
"""
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone


def _minute_key(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")


class Aggregator:
    def __init__(self, rate_window_sec: int = 10):
        self._lock = threading.Lock()
        self.rate_window = rate_window_sec
        self.reset()

    def reset(self):
        with self._lock:
            self.total_events = 0
            self.total_cost = 0.0
            self.by_service = defaultdict(lambda: {"events": 0, "cost": 0.0, "units": 0.0})
            self.by_region = defaultdict(lambda: {"events": 0, "cost": 0.0, "units": 0.0})
            self.by_minute = defaultdict(lambda: {"events": 0, "cost": 0.0})
            self._rate_samples = deque()  # (timestamp, count)

    def ingest(self, events: list[dict]) -> int:
        now = time.time()
        with self._lock:
            for e in events:
                cost = float(e.get("cost", 0.0))
                units = float(e.get("units", 0.0))
                self.total_events += 1
                self.total_cost += cost
                for dim_map, key in ((self.by_service, e.get("service", "unknown")),
                                     (self.by_region, e.get("region", "unknown"))):
                    d = dim_map[key]
                    d["events"] += 1
                    d["cost"] += cost
                    d["units"] += units
                ts = float(e["ts"]) if e.get("ts") is not None else now
                m = self.by_minute[_minute_key(ts)]
                m["events"] += 1
                m["cost"] += cost
            self._rate_samples.append((now, len(events)))
            self._trim_rate(now)
            return len(events)

    def _trim_rate(self, now: float):
        cutoff = now - self.rate_window
        while self._rate_samples and self._rate_samples[0][0] < cutoff:
            self._rate_samples.popleft()

    def _rate_locked(self, now: float) -> float:
        """Compute the live rate. Caller must already hold the lock."""
        self._trim_rate(now)
        counted = sum(c for _, c in self._rate_samples)
        return round(counted / self.rate_window, 1)

    def events_per_sec(self) -> float:
        with self._lock:
            return self._rate_locked(time.time())

    def summary(self) -> dict:
        with self._lock:
            return {
                "total_events": self.total_events,
                "total_cost": round(self.total_cost, 2),
                "distinct_services": len(self.by_service),
                "distinct_regions": len(self.by_region),
                "events_per_sec": self._rate_locked(time.time()),
            }

    def by_dimension(self, dim: str) -> list[dict]:
        source = {"service": self.by_service, "region": self.by_region}.get(dim)
        if source is None:
            raise ValueError("dim must be 'service' or 'region'")
        with self._lock:
            rows = [{"dimension": k, "events": v["events"],
                     "cost": round(v["cost"], 2), "units": round(v["units"], 2)}
                    for k, v in source.items()]
        return sorted(rows, key=lambda r: r["events"], reverse=True)

    def timeseries(self, minutes: int = 30) -> list[dict]:
        with self._lock:
            keys = sorted(self.by_minute.keys())[-minutes:]
            return [{"minute": k, "events": self.by_minute[k]["events"],
                     "cost": round(self.by_minute[k]["cost"], 2)} for k in keys]


# single process-wide instance
aggregator = Aggregator()
