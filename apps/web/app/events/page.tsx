"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type EventRow = {
  id: string;
  ingest_job_id: number;
  occurred_at: string | null;
  occurred_at_quality: string;
  event_type: string;
  src_player_id: string | null;
  dst_player_id: string | null;
  item: string | null;
  container: string | null;
  money: number | null;
  qty: number | null;
  raw_block_id: string;
  raw_line_index: number;
};

type Evidence = {
  line: string;
  context_before: string[];
  context_after: string[];
};

export default function EventsPage() {
  const searchParams = useSearchParams();
  const [rows, setRows] = useState<EventRow[]>([]);
  const [filters, setFilters] = useState({
    ingest_job_id: searchParams.get("ingest_job_id") ?? "",
    event_type: "",
    player_id: "",
    container_id: "",
    item_id: "",
    start: "",
    end: "",
  });
  const [selected, setSelected] = useState<EventRow | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      }
    });
    return params.toString();
  }, [filters]);

  const loadEvents = async () => {
    const response = await fetch(`${API_BASE}/events?${query}`);
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    setRows(data);
  };

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      ingest_job_id: searchParams.get("ingest_job_id") ?? prev.ingest_job_id,
    }));
  }, [searchParams]);

  useEffect(() => {
    loadEvents();
  }, [query]);

  const openEvidence = async (row: EventRow) => {
    setSelected(row);
    const response = await fetch(
      `${API_BASE}/evidence/raw-line?raw_block_id=${row.raw_block_id}&line_index=${row.raw_line_index}&context=2`
    );
    if (!response.ok) {
      setEvidence(null);
      return;
    }
    setEvidence(await response.json());
  };

  return (
    <div>
      <h1>Events Explorer</h1>
      <p>Filtre server-side + Evidence Drawer pentru linia raw.</p>
      <div className="section card">
        <h3>Filters</h3>
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          <input
            placeholder="ingest_job_id"
            value={filters.ingest_job_id}
            onChange={(event) => setFilters({ ...filters, ingest_job_id: event.target.value })}
          />
          <input
            placeholder="event_type"
            value={filters.event_type}
            onChange={(event) => setFilters({ ...filters, event_type: event.target.value })}
          />
          <input
            placeholder="player_id"
            value={filters.player_id}
            onChange={(event) => setFilters({ ...filters, player_id: event.target.value })}
          />
          <input
            placeholder="container_id"
            value={filters.container_id}
            onChange={(event) => setFilters({ ...filters, container_id: event.target.value })}
          />
          <input
            placeholder="item_id"
            value={filters.item_id}
            onChange={(event) => setFilters({ ...filters, item_id: event.target.value })}
          />
          <input
            placeholder="start (ISO)"
            value={filters.start}
            onChange={(event) => setFilters({ ...filters, start: event.target.value })}
          />
          <input
            placeholder="end (ISO)"
            value={filters.end}
            onChange={(event) => setFilters({ ...filters, end: event.target.value })}
          />
        </div>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Type</th>
            <th>Src</th>
            <th>Dst</th>
            <th>Money</th>
            <th>Qty</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} onClick={() => openEvidence(row)} style={{ cursor: "pointer" }}>
              <td>{row.occurred_at ?? "-"}</td>
              <td>{row.event_type}</td>
              <td>{row.src_player_id ?? "-"}</td>
              <td>{row.dst_player_id ?? "-"}</td>
              <td>{row.money ?? "-"}</td>
              <td>{row.qty ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {selected && (
        <div className="section card">
          <h3>Evidence for {selected.event_type}</h3>
          {evidence ? (
            <div>
              <div className="card" style={{ marginBottom: 12 }}>
                {evidence.context_before.map((line, idx) => (
                  <div key={`before-${idx}`}>{line}</div>
                ))}
                <div style={{ color: "#f97316", fontWeight: 600 }}>{evidence.line}</div>
                {evidence.context_after.map((line, idx) => (
                  <div key={`after-${idx}`}>{line}</div>
                ))}
              </div>
            </div>
          ) : (
            <p>Loading evidence...</p>
          )}
        </div>
      )}
    </div>
  );
}
