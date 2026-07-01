"use client";

import { topicColor } from "@/lib/utils";

const TRENDING = [
  { topic: "distributed-systems", label: "Distributed Systems", count: "29 concepts" },
  { topic: "databases",           label: "Databases",           count: "38 concepts" },
  { topic: "networking",          label: "Networking",          count: "42 concepts" },
  { topic: "caching",             label: "Caching",             count: "18 concepts" },
  { topic: "consistency",         label: "Consistency",         count: "15 concepts" },
  { topic: "messaging",           label: "Messaging",           count: "12 concepts" },
];

const SUGGESTIONS = [
  { name: "CAP Theorem",       slug: "cap-theorem",        topic: "distributed-systems" },
  { name: "Consistent Hashing",slug: "consistent-hashing", topic: "distributed-systems" },
  { name: "Kafka",             slug: "kafka",               topic: "messaging"           },
  { name: "Raft",              slug: "raft",                topic: "distributed-systems" },
];

export function RightSidebar() {
  return (
    <aside
      style={{
        width: 350, flexShrink: 0,
        padding: "12px 20px",
        overflowY: "auto", height: "100%",
        scrollbarWidth: "none",
      }}
      className="hidden lg:block"
    >
      {/* Search */}
      <div style={{
        position: "relative", marginBottom: 16,
      }}>
        <div style={{
          position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)",
          color: "var(--text-muted)", pointerEvents: "none",
          display: "flex", alignItems: "center",
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
        </div>
        <input
          placeholder="Search system design"
          style={{
            width: "100%", padding: "12px 16px 12px 42px",
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 99, color: "var(--text)", fontSize: 15,
            outline: "none", boxSizing: "border-box",
          }}
          onFocus={e => (e.currentTarget.style.borderColor = "var(--border-strong)")}
          onBlur={e => (e.currentTarget.style.borderColor = "var(--border)")}
        />
      </div>

      {/* Trending */}
      <div className="sidebar-card">
        <div className="sidebar-card-header">Trending in System Design</div>
        {TRENDING.map(({ topic, label, count }) => (
          <div key={topic} className="sidebar-row">
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 2 }}>System Design</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text)" }}>#{label}</div>
            <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 2 }}>{count}</div>
          </div>
        ))}
      </div>

      {/* Suggested concepts */}
      <div className="sidebar-card">
        <div className="sidebar-card-header">Explore concepts</div>
        {SUGGESTIONS.map(({ name, slug, topic }) => {
          const color = topicColor(topic);
          return (
            <div key={slug} className="sidebar-row" style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{
                width: 44, height: 44, borderRadius: "50%", flexShrink: 0,
                background: `${color}22`, border: `1.5px solid ${color}55`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18,
              }}>
                🔷
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text)" }}>{name}</div>
                <div style={{ fontSize: 13, color: "var(--text-muted)" }}>@{slug}</div>
              </div>
              <button style={{
                padding: "6px 16px", borderRadius: 99,
                border: "1px solid var(--border-strong)",
                background: "none", color: "var(--text)",
                fontSize: 14, fontWeight: 700, cursor: "pointer",
                transition: "background 0.12s",
              }}>
                Follow
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
