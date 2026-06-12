"use client";

import { Bookmark, BarChart2, Heart, MessageCircle, Repeat2, Share2 } from "lucide-react";

export interface CardData {
  id: string;
  node_id: string;
  node_slug: string;
  topic: string;
  hook: string;
  body: string;
  format: string;
}

const TOPIC_META: Record<string, { color: string; bg: string; initials: string }> = {
  networking:            { color: "#6b9ab8", bg: "rgba(107,154,184,0.15)", initials: "NW" },
  caching:               { color: "#b89a5a", bg: "rgba(184,154,90,0.15)",  initials: "CH" },
  databases:             { color: "#5aa87a", bg: "rgba(90,168,122,0.15)",  initials: "DB" },
  "distributed-systems": { color: "#9b8fc4", bg: "rgba(155,143,196,0.15)", initials: "DS" },
  consistency:           { color: "#c47080", bg: "rgba(196,112,128,0.15)", initials: "CS" },
  messaging:             { color: "#5ab0b0", bg: "rgba(90,176,176,0.15)",  initials: "MQ" },
};

const FORMAT_LABEL: Record<string, string> = {
  pattern:    "Pattern",
  war_story:  "War Story",
  tradeoff:   "Tradeoff",
  comparison: "Comparison",
  quiz:       "Quiz",
  analogy:    "Analogy",
  meme:       "Meme",
  thread:     "Thread",
};

function slugToName(slug: string): string {
  return slug.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function EngageBtn({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  return (
    <button aria-label={label} className="engage-btn">
      <Icon size={17} />
    </button>
  );
}

export function FeedCard({ card }: { card: CardData }) {
  const meta = TOPIC_META[card.topic] ?? { color: "#72747f", bg: "rgba(114,116,127,0.15)", initials: "SD" };
  const displayName = slugToName(card.node_slug);
  const formatLabel = FORMAT_LABEL[card.format] ?? card.format;

  return (
    <article
      className="tweet-card"
      style={{
        padding: "16px 20px",
        borderBottom: "1px solid var(--border)",
        display: "flex", gap: 12,
      }}
    >
      {/* Avatar */}
      <div style={{
        width: 44, height: 44, borderRadius: "50%", flexShrink: 0,
        background: meta.bg, border: `1.5px solid ${meta.color}55`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 12, fontWeight: 800, color: meta.color,
        letterSpacing: "0.04em",
      }}>
        {meta.initials}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 4, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 700, fontSize: 15, color: "var(--text)" }}>{displayName}</span>
          <span style={{ fontSize: 14, color: "var(--text-muted)" }}>@{card.node_slug}</span>
          <span style={{
            marginLeft: "auto",
            fontSize: 11, fontWeight: 600,
            color: meta.color, background: meta.bg,
            padding: "2px 8px", borderRadius: 99,
          }}>
            {formatLabel}
          </span>
        </div>

        {/* Hook */}
        <p style={{ margin: "0 0 6px", fontSize: 15, lineHeight: 1.5, color: "var(--text)", fontWeight: 500 }}>
          {card.hook}
        </p>

        {/* Body */}
        <p style={{ margin: "0 0 14px", fontSize: 14, lineHeight: 1.65, color: "var(--text-muted)" }}>
          {card.body}
        </p>

        {/* Engagement row */}
        <div style={{ display: "flex", justifyContent: "space-between", maxWidth: 360 }}>
          <EngageBtn icon={MessageCircle} label="Reply" />
          <EngageBtn icon={Repeat2}       label="Repost" />
          <EngageBtn icon={Heart}         label="Like" />
          <EngageBtn icon={BarChart2}     label="Views" />
          <EngageBtn icon={Bookmark}      label="Bookmark" />
          <EngageBtn icon={Share2}        label="Share" />
        </div>
      </div>
    </article>
  );
}
