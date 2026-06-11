"""API contract for PulseMeter."""
from typing import Optional
from pydantic import BaseModel, Field


class Event(BaseModel):
    service: str
    region: str
    event_type: str = "request"
    cost: float = Field(default=0.0, ge=0)
    units: float = Field(default=0.0, ge=0)
    ts: Optional[float] = None  # unix seconds; defaults to ingest time


class IngestBatch(BaseModel):
    events: list[Event]


class IngestResult(BaseModel):
    accepted: int
    total_events: int


class Summary(BaseModel):
    total_events: int
    total_cost: float
    distinct_services: int
    distinct_regions: int
    events_per_sec: float


class DimRow(BaseModel):
    dimension: str
    events: int
    cost: float
    units: float


class TimePoint(BaseModel):
    minute: str
    events: int
    cost: float
