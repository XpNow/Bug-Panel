"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function chunkFile(file: File, chunkSize: number) {
  const chunks: { index: number; blob: Blob }[] = [];
  let index = 0;
  for (let offset = 0; offset < file.size; offset += chunkSize) {
    chunks.push({ index, blob: file.slice(offset, offset + chunkSize) });
    index += 1;
  }
  return chunks;
}

export default function ImportsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [jobs, setJobs] = useState<any[]>([]);
  const [activeJob, setActiveJob] = useState<any | null>(null);

  const pollJobs = async () => {
    const response = await fetch(`${API_BASE}/ingest-jobs`);
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    setJobs(data);
  };

  useEffect(() => {
    pollJobs();
    const handle = setInterval(pollJobs, 2000);
    return () => clearInterval(handle);
  }, []);

  const uploadFile = async () => {
    if (!file) {
      return;
    }
    setStatus("Creating upload session...");
    const chunkSize = 5 * 1024 * 1024;
    const chunks = chunkFile(file, chunkSize);
    const create = await fetch(`${API_BASE}/uploads/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: file.name,
        size: file.size,
        chunk_size: chunkSize,
        expected_chunks: chunks.length,
      }),
    });
    if (!create.ok) {
      setStatus("Failed to create upload.");
      return;
    }
    const session = await create.json();

    const concurrent = 3;
    let cursor = 0;
    const uploadChunk = async () => {
      while (cursor < chunks.length) {
        const current = chunks[cursor];
        cursor += 1;
        const buffer = await current.blob.arrayBuffer();
        setStatus(`Uploading chunk ${current.index + 1}/${chunks.length}`);
        await fetch(`${API_BASE}/uploads/${session.id}/chunk?index=${current.index}`, {
          method: "PUT",
          body: buffer,
        });
      }
    };
    await Promise.all(Array.from({ length: concurrent }, () => uploadChunk()));

    setStatus("Finalizing upload...");
    const finalize = await fetch(`${API_BASE}/uploads/${session.id}/finalize`, { method: "POST" });
    if (!finalize.ok) {
      setStatus("Finalize failed.");
      return;
    }
    const sourceFile = await finalize.json();
    setStatus("Creating ingest job...");
    const jobResp = await fetch(`${API_BASE}/ingest-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_file_id: sourceFile.id }),
    });
    if (!jobResp.ok) {
      setStatus("Failed to create ingest job.");
      return;
    }
    const job = await jobResp.json();
    setActiveJob(job);
    setStatus(`Job ${job.id} created.`);
    pollJobs();
  };

  const activeStats = useMemo(() => {
    if (!activeJob?.id) {
      return null;
    }
    const job = jobs.find((item) => item.id === activeJob.id) ?? activeJob;
    return job.stats_json ?? null;
  }, [activeJob, jobs]);

  return (
    <div>
      <h1>Imports</h1>
      <p>Upload transcripturi mari si porneste ingest-ul direct din UI.</p>
      <div className="section card">
        <h3>Upload</h3>
        <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        <button onClick={uploadFile} style={{ marginLeft: 12 }}>
          Upload + Ingest
        </button>
        {status && <p>{status}</p>}
      </div>
      <div className="section card">
        <h3>Ingest Jobs</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Source File</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.id}</td>
                <td>{job.status}</td>
                <td>{job.source_file_id}</td>
                <td>{job.created_at}</td>
                <td>
                  <button onClick={() => setActiveJob(job)}>Details</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {activeJob && (
        <div className="section card">
          <h3>Job Details #{activeJob.id}</h3>
          <p>Status: {activeJob.status}</p>
          {activeStats && (
            <div>
              <h4>Event Types</h4>
              <ul>
                {(activeStats.event_type_counts ?? []).map(([key, count]: [string, number]) => (
                  <li key={key}>
                    {key}: {count}
                  </li>
                ))}
              </ul>
              <h4>Unknown Signatures</h4>
              <ul>
                {(activeStats.unknown_signatures ?? []).map(([key, count]: [string, number]) => (
                  <li key={key}>
                    {key} ({count})
                  </li>
                ))}
              </ul>
            </div>
          )}
          <a href={`/events?ingest_job_id=${activeJob.id}`}>View events for this job</a>
        </div>
      )}
    </div>
  );
}
