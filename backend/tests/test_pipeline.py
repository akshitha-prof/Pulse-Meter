"""Tests for the aggregator core and the ingest/metrics API."""
import pytest
from fastapi.testclient import TestClient

from app.aggregator import Aggregator
from app.main import app, aggregator

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean():
    aggregator.reset()
    yield


# ---- aggregator unit tests ----
def test_ingest_counts_and_dims():
    agg = Aggregator()
    agg.ingest([
        {"service": "search", "region": "apac", "cost": 1.0, "units": 10},
        {"service": "search", "region": "emea", "cost": 2.0, "units": 5},
        {"service": "ads", "region": "apac", "cost": 0.5, "units": 1},
    ])
    s = agg.summary()
    assert s["total_events"] == 3
    assert s["total_cost"] == 3.5
    assert s["distinct_services"] == 2
    by_service = agg.by_dimension("service")
    assert by_service[0]["dimension"] == "search"  # sorted desc by events
    assert by_service[0]["events"] == 2


def test_bad_dimension_raises():
    with pytest.raises(ValueError):
        Aggregator().by_dimension("nonsense")


def test_timeseries_buckets_by_minute():
    agg = Aggregator()
    agg.ingest([{"service": "s", "region": "r", "cost": 1, "ts": 1_700_000_000}])
    agg.ingest([{"service": "s", "region": "r", "cost": 1, "ts": 1_700_000_005}])  # same minute
    ts = agg.timeseries()
    assert len(ts) == 1 and ts[0]["events"] == 2


# ---- API tests ----
def test_ingest_endpoint_and_summary():
    body = {"events": [{"service": "compute", "region": "us", "cost": 0.1, "units": 3}]}
    r = client.post("/api/ingest", json=body)
    assert r.status_code == 200
    assert r.json() == {"accepted": 1, "total_events": 1}
    assert client.get("/api/metrics/summary").json()["total_events"] == 1


def test_by_dimension_endpoint():
    client.post("/api/ingest", json={"events": [
        {"service": "a", "region": "r"}, {"service": "a", "region": "r"}, {"service": "b", "region": "r"},
    ]})
    rows = client.get("/api/metrics/by?dim=service").json()
    assert rows[0]["dimension"] == "a" and rows[0]["events"] == 2


def test_by_dimension_bad_request():
    assert client.get("/api/metrics/by?dim=oops").status_code == 400


def test_throughput_smoke():
    # push 5k events through the API and confirm they're all counted
    for _ in range(5):
        client.post("/api/ingest", json={"events": [
            {"service": "search", "region": "apac", "cost": 0.01} for _ in range(1000)]})
    assert client.get("/api/metrics/summary").json()["total_events"] == 5000
