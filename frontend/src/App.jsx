import { useEffect, useState, useCallback } from "react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { api, fmt, fmtMoney } from "./api.jsx";

const POLL_MS = 2000;

export default function App() {
  const [summary, setSummary] = useState(null);
  const [series, setSeries] = useState([]);
  const [byRows, setByRows] = useState([]);
  const [dim, setDim] = useState("service");
  const [connected, setConnected] = useState(false);

  const poll = useCallback(async () => {
    try {
      const [s, ts, by] = await Promise.all([
        api.get("/api/metrics/summary"),
        api.get("/api/metrics/timeseries", { params: { minutes: 30 } }),
        api.get("/api/metrics/by", { params: { dim } }),
      ]);
      setSummary(s.data);
      setSeries(ts.data.map((p) => ({ ...p, label: p.minute.slice(11) })));
      setByRows(by.data);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }, [dim]);

  useEffect(() => {
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => clearInterval(id);
  }, [poll]);

  const hasData = summary && summary.total_events > 0;

  return (
    <div className="wrap">
      <div className="top">
        <div className="logo"><span className="pulse" /> PulseMeter</div>
        <div className="live">
          <span className="pulse" style={{ background: connected ? "var(--accent)" : "var(--warn)" }} />
          {connected ? "live · refreshing every 2s" : "API offline"}
        </div>
      </div>
      <div className="sub">Real-time telemetry ingestion &amp; analytics — cloud service usage monitor.</div>

      <div className="cards">
        <div className="card"><div className="k">Total events</div><div className="v accent">{fmt(summary?.total_events)}</div></div>
        <div className="card"><div className="k">Ingest rate</div><div className="v">{fmt(summary?.events_per_sec)}<span style={{ fontSize: 14, color: "var(--ink-soft)" }}> /s</span></div></div>
        <div className="card"><div className="k">Tracked cost</div><div className="v">{fmtMoney(summary?.total_cost)}</div></div>
        <div className="card"><div className="k">Services</div><div className="v">{fmt(summary?.distinct_services)}</div></div>
        <div className="card"><div className="k">Regions</div><div className="v">{fmt(summary?.distinct_regions)}</div></div>
      </div>

      {!hasData && (
        <div className="panel">
          <div className="panel-head"><h3>Waiting for events</h3></div>
          <p className="hintbox">
            No events ingested yet. Start the backend, then push synthetic load:<br />
            <code>cd backend</code> · <code>uvicorn app.main:app --reload</code><br />
            <code>python -m app.loadgen --n 300000 --batch 3000</code><br />
            The dashboard updates automatically as events arrive.
          </p>
        </div>
      )}

      <div className="panel">
        <div className="panel-head"><h3>Events per minute</h3></div>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={series} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <defs>
              <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#36e0b0" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#36e0b0" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2636" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#8593a8" }} />
            <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: "#8593a8" }} />
            <Tooltip contentStyle={{ background: "#121826", border: "1px solid #1e2636", borderRadius: 8, color: "#e6edf6" }}
              formatter={(v) => fmt(v)} />
            <Area type="monotone" dataKey="events" stroke="#36e0b0" strokeWidth={2} fill="url(#g)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h3>Breakdown by {dim}</h3>
          <div className="seg">
            <button className={dim === "service" ? "on" : ""} onClick={() => setDim("service")}>service</button>
            <button className={dim === "region" ? "on" : ""} onClick={() => setDim("region")}>region</button>
          </div>
        </div>
        {byRows.length === 0 ? <div className="empty">No data yet.</div> : (
          <>
            <ResponsiveContainer width="100%" height={Math.max(160, byRows.length * 34)}>
              <BarChart data={byRows} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2636" horizontal={false} />
                <XAxis type="number" tickFormatter={fmt} tick={{ fontSize: 11, fill: "#8593a8" }} />
                <YAxis type="category" dataKey="dimension" width={110} tick={{ fontSize: 12, fill: "#e6edf6" }} />
                <Tooltip contentStyle={{ background: "#121826", border: "1px solid #1e2636", borderRadius: 8, color: "#e6edf6" }}
                  formatter={(v) => fmt(v)} />
                <Bar dataKey="events" fill="#5b8cff" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <table>
              <thead><tr><th>{dim}</th><th className="num">Events</th><th className="num">Cost</th><th className="num">Units</th></tr></thead>
              <tbody>
                {byRows.map((r) => (
                  <tr key={r.dimension}>
                    <td>{r.dimension}</td>
                    <td className="num">{fmt(r.events)}</td>
                    <td className="num">{fmtMoney(r.cost)}</td>
                    <td className="num">{fmt(r.units)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}
