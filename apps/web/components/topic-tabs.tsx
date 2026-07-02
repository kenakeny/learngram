"use client";

import { useState } from "react";
import { FeedCard, type CardData } from "@/components/feed-card";
import { topicColor } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface TopicCount {
  topic: string;
  cards: number;
  nodes: number;
}

// null topic == "For You" (unfiltered)
type Selected = string | null;

export function TopicTabs({
  initialCards,
  initialTopics,
}: {
  initialCards: CardData[];
  initialTopics: TopicCount[];
}) {
  const [topics] = useState<TopicCount[]>(initialTopics);
  const [selected, setSelected] = useState<Selected>(null);
  const [cards, setCards] = useState<CardData[]>(initialCards);
  const [loading, setLoading] = useState(false);

  async function selectTopic(topic: Selected) {
    if (topic === selected) return;
    setSelected(topic);
    setLoading(true);
    try {
      const url =
        topic === null
          ? `${API}/feed?limit=20`
          : `${API}/feed?topic=${encodeURIComponent(topic)}&limit=20`;
      const res = await fetch(url, { cache: "no-store" });
      const data = res.ok ? await res.json() : { cards: [] };
      setCards(data.cards ?? []);
    } catch {
      setCards([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="feed-scroll">
      {/* Sticky tab header */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "rgba(13,13,15,0.85)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 8,
            padding: "10px 16px",
            overflowX: "auto",
            scrollbarWidth: "none",
          }}
        >
          <Chip
            label="For You"
            active={selected === null}
            color="var(--text)"
            onClick={() => selectTopic(null)}
          />
          {topics.map((t) => (
            <Chip
              key={t.topic}
              label={t.topic}
              active={selected === t.topic}
              color={topicColor(t.topic)}
              onClick={() => selectTopic(t.topic)}
            />
          ))}
        </div>
      </div>

      {loading ? (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            padding: "48px 24px",
            color: "var(--text-muted)",
            fontSize: 14,
          }}
        >
          Loading…
        </div>
      ) : cards.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            padding: "80px 24px",
            color: "var(--text-muted)",
          }}
        >
          <span style={{ fontSize: 32 }}>📡</span>
          <p style={{ fontSize: 14, margin: 0 }}>
            {selected === null
              ? "API not reachable — is it running on :8000?"
              : "No cards for this topic yet."}
          </p>
        </div>
      ) : (
        cards.map((card) => <FeedCard key={card.id} card={card} />)
      )}
    </div>
  );
}

function Chip({
  label,
  active,
  color,
  onClick,
}: {
  label: string;
  active: boolean;
  color: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 14px",
        borderRadius: 99,
        fontSize: 14,
        fontWeight: 600,
        cursor: "pointer",
        whiteSpace: "nowrap",
        color: active ? "var(--bg)" : "var(--text)",
        background: active ? color : "var(--surface-2)",
        border: `1px solid ${active ? color : "var(--border)"}`,
        transition: "background 0.15s, color 0.15s",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
          flexShrink: 0,
          opacity: active ? 0.9 : 1,
        }}
      />
      {label}
    </button>
  );
}
