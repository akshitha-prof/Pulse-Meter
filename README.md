# PulseMeter — high-throughput telemetry ingestion & live analytics

A full-stack monitoring tool that **ingests a stream of telemetry events**
(synthetic cloud service usage), folds them into **rolling aggregates**, and
serves **live metrics** to a React dashboard. Built to demonstrate web-scale data
ingestion: on a single process it sustains **50,000+ events/sec** — well past
millions of events per day.

> **Read this first.** This is a reference implementation to learn from and
> extend. Run it, read every file, and make it yours before putting it on a
> resume — an interviewer will ask you to defend the design.

## What it does
- **Batch ingest API** (`POST /api/ingest`) that folds events into in-memory rollups under a single lock — high throughput without storing every row.
- **Live metrics**: total events, ingest rate (events/sec over a rolling window), tracked cost, breakdowns by service and region, and a per-minute time series.
- **Load generator** (`loadgen.py`) that pushes synthetic events and reports measured throughput and implied events/day.
- **React dashboard** that polls every 2s — summary cards, an events-per-minute area chart, and a service/region breakdown.

## Measured performance
```
$ python -m app.loadgen --n 300000 --batch 3000
Sent 300,000 events in 5.6s
Throughput: 53,531 events/sec  ->  ~4,625M events/day
```
(Single process, in-memory aggregation. Numbers vary by machine.)

## Architecture
```
loadgen.py --batch POST--> FastAPI /api/ingest --> Aggregator (thread-safe rollups)
                                                       |  by_service / by_region
React dashboard <--poll /metrics-- FastAPI <-----------+  by_minute + live rate
```
The `Aggregator` is the heart of the project: events fold into counters keyed by
dimension and by minute instead of being persisted row-by-row. That shape maps
cleanly onto a `GROUP BY` — so the natural production step is to **flush rollups
to a columnar store (BigQuery / ClickHouse)** on an interval.

## Tech stack
| Layer | Tech |
|-------|------|
| Backend | FastAPI, Pydantic v2 |
| Aggregation | Pure Python, thread-safe (`threading.Lock`) |
| Frontend | React 18, Vite, Recharts, Axios |
| Load testing | httpx-based generator |
| Tests | pytest + FastAPI TestClient |

## Quickstart

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000  (docs at /docs)
```
### Generate load (new terminal)
```bash
cd backend && source .venv/bin/activate
python -m app.loadgen --n 300000 --batch 3000
```
### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 — watch the numbers climb live
```
### Tests
```bash
cd backend && pytest -q
```

## API
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/ingest` | Ingest a batch of events |
| GET  | `/api/metrics/summary` | Totals + live ingest rate |
| GET  | `/api/metrics/by?dim=service\|region` | Aggregates per dimension |
| GET  | `/api/metrics/timeseries?minutes=30` | Per-minute counts |
| POST | `/api/reset` | Clear all counters (demo) |

## Project structure
```
backend/app/
  main.py         FastAPI routes + CORS
  aggregator.py   thread-safe streaming aggregator (the core)
  schemas.py      Pydantic event + metrics contracts
  loadgen.py      synthetic load generator / throughput benchmark
backend/tests/test_pipeline.py
frontend/src/
  App.jsx         live dashboard (cards, area chart, breakdown)
  api.jsx, styles.css
```

## How this maps to the job (and your resume)
Built against a Google **Application Engineer, Full Stack** posting; targets the
preferred qual: *"web-scale databases and building data pipelines capable of
aggregating and processing millions of events per day."*

**Sample resume bullets** (keep only what stays true as you extend it):
- *Built a telemetry ingestion + analytics pipeline (FastAPI, React) that sustains 50k+ events/sec in a single process and serves live aggregated metrics to a React dashboard; validated throughput with a custom load generator.*
- *Designed a thread-safe streaming aggregator that folds events into rolling rollups by dimension and minute, mapping directly onto a columnar `GROUP BY`.*

## Make it yours
1. Flush rollups to **BigQuery / Postgres** on an interval; query history from there.
2. Add **percentiles** (p50/p95/p99) and an **error-rate** alert threshold.
3. Replace in-process ingest with **Google Pub/Sub** + a worker.
4. Add **WebSocket push** instead of polling for true real-time updates.
5. Containerize and deploy to **Cloud Run**; add a CI workflow.

## Interview prep
- Why aggregate in memory instead of storing every event? (throughput; trade-off: durability/restart loss)
- How does the rolling ingest-rate window work, and why a deque?
- Where's the concurrency boundary, and why one lock? When does it bottleneck? (shard by key, lock-striping, or per-worker rollups merged downstream)
- How would you make this horizontally scalable and durable? (Pub/Sub + stateless workers + columnar sink)

## Notes / limitations
- Aggregates live in process memory — restarting clears them. Intentional for a demo; the extensions above show the path to durability.
- A single lock is fine to tens of thousands of events/sec; beyond that, shard the state. Called out deliberately as a known trade-off.
