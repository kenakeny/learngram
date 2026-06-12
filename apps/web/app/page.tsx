import { FeedCard, type CardData } from "@/components/feed-card";

async function getFeed(): Promise<CardData[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/feed?limit=20`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.cards ?? [];
  } catch {
    return [];
  }
}

export default async function Home() {
  const cards = await getFeed();

  return (
    <div className="feed-scroll">
      {/* Sticky tab header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 10,
        background: "rgba(13,13,15,0.85)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
      }}>
        <button className="feed-tab active">For You</button>
        <button className="feed-tab" disabled style={{ opacity: 0.45, cursor: "default" }}>By Topic</button>
      </div>

      {cards.length === 0 ? (
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          justifyContent: "center", gap: 12, padding: "80px 24px",
          color: "var(--text-muted)",
        }}>
          <span style={{ fontSize: 32 }}>📡</span>
          <p style={{ fontSize: 14, margin: 0 }}>API not reachable — is it running on :8000?</p>
        </div>
      ) : (
        cards.map(card => <FeedCard key={card.id} card={card} />)
      )}
    </div>
  );
}
