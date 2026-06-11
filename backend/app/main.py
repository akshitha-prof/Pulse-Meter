"""PulseMeter API — high-throughput event ingestion + live analytics."""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .aggregator import aggregator
from .schemas import IngestBatch, IngestResult, Summary, DimRow, TimePoint

app = FastAPI(
    title="PulseMeter API",
    version="1.0.0",
    description="Ingest telemetry events and serve live aggregated metrics.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


@app.post("/api/ingest", response_model=IngestResult)
def ingest(batch: IngestBatch):
    n = aggregator.ingest([e.model_dump() for e in batch.events])
    return IngestResult(accepted=n, total_events=aggregator.total_events)


@app.get("/api/metrics/summary", response_model=Summary)
def summary():
    return aggregator.summary()


@app.get("/api/metrics/by", response_model=list[DimRow])
def by_dimension(dim: str = Query("service")):
    try:
        return aggregator.by_dimension(dim)
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.get("/api/metrics/timeseries", response_model=list[TimePoint])
def timeseries(minutes: int = Query(30, ge=1, le=1440)):
    return aggregator.timeseries(minutes)


@app.post("/api/reset")
def reset():
    aggregator.reset()
    return {"status": "reset"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
