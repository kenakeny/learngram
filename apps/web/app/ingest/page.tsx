"use client";

import { useCallback, useRef, useState } from "react";
import { CheckCircle2, FileUp, Loader2, TriangleAlert } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ACCEPT = ".md,.markdown,.txt,.pdf,.docx,.pptx,.html,.htm";

interface Job {
  id: string;
  filename: string;
  status: "pending" | "running" | "done" | "error";
  step: string;
  message: string;
  nodes_added: number;
  cards_added: number;
}

const STEP_LABEL: Record<string, string> = {
  queued: "Queued",
  convert: "Converting file",
  extract: "Reading & extracting concepts",
  approve: "Building the knowledge graph",
  embed: "Embedding for retrieval",
  generate: "Writing cards",
  done: "Done",
  error: "Error",
};

export default function IngestPage() {
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const poll = useCallback(async (jobId: string) => {
    // Poll until the job reaches a terminal state.
    while (true) {
      await new Promise(r => setTimeout(r, 1500));
      const res = await fetch(`${API}/ingest/${jobId}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const j: Job = await res.json();
      setJob(j);
      if (j.status === "done" || j.status === "error") return j;
    }
  }, []);

  const upload = useCallback(async (file: File) => {
    setBusy(true);
    setError(null);
    setJob(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/ingest`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`upload failed (${res.status})`);
      const { job_id } = await res.json();
      setJob({ id: job_id, filename: file.name, status: "running", step: "queued", message: "", nodes_added: 0, cards_added: 0 });
      await poll(job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "something went wrong");
    } finally {
      setBusy(false);
    }
  }, [poll]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && !busy) upload(file);
  }, [busy, upload]);

  const done = job?.status === "done";
  const failed = job?.status === "error" || !!error;
  const running = busy || (job != null && job.status !== "done" && job.status !== "error");

  return (
    <div style={{ height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 10,
        background: "rgba(13,13,15,0.85)", backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
        padding: "14px 20px",
      }}>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: "var(--text)" }}>Ingest</h1>
        <p style={{ margin: "2px 0 0", fontSize: 13, color: "var(--text-muted)" }}>
          Drop a Markdown or PDF and it becomes feed cards automatically.
        </p>
      </div>

      <div style={{ padding: "24px 20px", display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Drop zone */}
        <div
          onClick={() => !running && inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          style={{
            border: `1.5px dashed ${dragging ? "var(--text)" : "var(--border-strong)"}`,
            borderRadius: 16,
            padding: "48px 24px",
            display: "flex", flexDirection: "column", alignItems: "center", gap: 12,
            cursor: running ? "default" : "pointer",
            background: dragging ? "var(--surface-2)" : "var(--surface)",
            transition: "background 0.15s, border-color 0.15s",
            opacity: running ? 0.6 : 1,
          }}
        >
          <FileUp size={32} color="var(--text-muted)" />
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>
            {running ? "Processing…" : "Drop a file or click to browse"}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            .md · .pdf · .docx · .pptx · .html · .txt
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            style={{ display: "none" }}
            onChange={e => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }}
          />
        </div>

        {/* Status */}
        {job && (
          <div style={{
            border: "1px solid var(--border)", borderRadius: 14,
            padding: "16px 18px", background: "var(--surface)",
            display: "flex", flexDirection: "column", gap: 10,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {done ? <CheckCircle2 size={20} color="#5aa87a" />
                : failed ? <TriangleAlert size={20} color="#c47080" />
                : <Loader2 size={20} color="var(--text-muted)" className="spin" />}
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text)" }}>
                  {STEP_LABEL[job.step] ?? job.step}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {job.filename}{job.message ? ` · ${job.message}` : ""}
                </div>
              </div>
            </div>

            {done && (
              <div style={{ display: "flex", gap: 20, alignItems: "center", paddingTop: 4 }}>
                <span style={{ fontSize: 14, color: "var(--text)" }}>
                  <b>{job.nodes_added}</b> concepts · <b>{job.cards_added}</b> cards
                </span>
                <a href="/" style={{
                  marginLeft: "auto",
                  fontSize: 14, fontWeight: 700, color: "var(--bg)",
                  background: "var(--text)", padding: "8px 16px", borderRadius: 99,
                  textDecoration: "none",
                }}>
                  View feed
                </a>
              </div>
            )}
          </div>
        )}

        {error && !job && (
          <div style={{ fontSize: 13, color: "#c47080" }}>{error}</div>
        )}

        <p style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
          Topics are decided by the AI — it reuses an existing topic when a concept
          fits, or creates a new one, so your topic set grows as you ingest.
        </p>
      </div>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
