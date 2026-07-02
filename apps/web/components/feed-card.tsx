"use client";

import { useState } from "react";
import { Bookmark, BarChart2, CheckCircle2, Heart, HelpCircle, MessageCircle, Repeat2, Share2, ThumbsDown } from "lucide-react";
import { topicBg, topicColor, topicInitials } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CardData {
  id: string;
  node_id: string;
  node_slug: string;
  topic: string;
  hook: string;
  body: string;
  format: string;
  // Persona ("account") that authored the post, when present.
  concept_name?: string | null;
  post_style?: string | null;
  persona_slug?: string | null;
  persona_name?: string | null;
  persona_color?: string | null;
  persona_emoji?: string | null;
}

const POST_STYLE_LABEL: Record<string, string> = {
  oneliner: "one-liner",
  rant: "rant",
  stackoverflow: "Stack Overflow",
  meme: "meme",
};

function slugToName(slug: string): string {
  return slug.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function EngageBtn({
  icon: Icon, label, onClick, active, activeColor,
}: {
  icon: React.ElementType; label: string; onClick?: () => void; active?: boolean; activeColor?: string;
}) {
  return (
    <button
      aria-label={label}
      aria-pressed={active}
      className="engage-btn"
      onClick={onClick}
      style={active && activeColor ? { color: activeColor } : undefined}
    >
      <Icon size={17} fill={active ? "currentColor" : "none"} />
    </button>
  );
}

/** Body layout differs per persona post style. */
function PostBody({ card }: { card: CardData }) {
  const style = card.post_style ?? "";

  if (style === "oneliner") {
    return (
      <p style={{ margin: "2px 0 14px", fontSize: 18, lineHeight: 1.45, color: "var(--text)", fontWeight: 600 }}>
        {card.hook}
      </p>
    );
  }

  if (style === "stackoverflow") {
    return (
      <div style={{ margin: "2px 0 14px" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 10 }}>
          <HelpCircle size={16} color="var(--text-muted)" style={{ marginTop: 2, flexShrink: 0 }} />
          <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--text)", lineHeight: 1.45 }}>{card.hook}</p>
        </div>
        <div style={{
          display: "flex", gap: 8, alignItems: "flex-start",
          borderLeft: "2px solid #5aa87a", paddingLeft: 10,
        }}>
          <CheckCircle2 size={16} color="#5aa87a" style={{ marginTop: 2, flexShrink: 0 }} />
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.65, color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>{card.body}</p>
        </div>
      </div>
    );
  }

  if (style === "meme") {
    return (
      <div style={{ margin: "2px 0 14px", textAlign: "center" }}>
        <p style={{ margin: "0 0 6px", fontSize: 16, fontWeight: 800, color: "var(--text)", lineHeight: 1.4, letterSpacing: "-0.01em" }}>
          {card.hook}
        </p>
        {card.body && (
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: "var(--text-muted)", fontStyle: "italic" }}>
            {card.body}
          </p>
        )}
      </div>
    );
  }

  // rant (and any unknown style): bold opener + body
  return (
    <div style={{ margin: "2px 0 14px" }}>
      <p style={{ margin: "0 0 6px", fontSize: 15, lineHeight: 1.5, color: "var(--text)", fontWeight: 600 }}>{card.hook}</p>
      {card.body && (
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.65, color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>{card.body}</p>
      )}
    </div>
  );
}

export function FeedCard({ card }: { card: CardData }) {
  const hasPersona = !!card.persona_slug;
  const topicHue = topicColor(card.topic);
  const conceptName = card.concept_name ?? slugToName(card.node_slug);

  // Author identity: persona account, or fall back to the concept itself.
  const authorColor = hasPersona ? (card.persona_color ?? "#72747f") : topicColor(card.topic);
  const authorName = hasPersona ? (card.persona_name ?? "") : conceptName;
  const authorHandle = hasPersona ? card.persona_slug! : card.node_slug;
  const avatarBg = `${authorColor}22`;

  const [vote, setVote] = useState<"up" | "down" | null>(null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState("");
  const [thanks, setThanks] = useState(false);
  const [sending, setSending] = useState(false);

  async function sendFeedback(rating: "up" | "down", commentText?: string) {
    setSending(true);
    try {
      await fetch(`${API}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: card.id, rating, comment: commentText || null }),
      });
      setThanks(true);
    } catch {
      // swallow — feedback is best-effort, never block the feed
    } finally {
      setSending(false);
    }
  }

  function handleUp() {
    if (vote === "up") return;
    setVote("up");
    setShowComment(false);
    void sendFeedback("up");
  }
  function handleDown() {
    if (vote === "down") { setShowComment(v => !v); return; }
    setVote("down");
    setThanks(false);
    setShowComment(true);
  }
  function submitComment() {
    void sendFeedback("down", comment.trim());
    setShowComment(false);
  }

  return (
    <article
      className="tweet-card"
      style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", gap: 12 }}
    >
      {/* Avatar */}
      <div style={{
        width: 44, height: 44, borderRadius: "50%", flexShrink: 0,
        background: avatarBg, border: `1.5px solid ${authorColor}55`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: hasPersona ? 22 : 12, fontWeight: 800, color: authorColor, letterSpacing: "0.04em",
      }}>
        {hasPersona ? (card.persona_emoji || "🙂") : topicInitials(card.topic)}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Header: author */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 700, fontSize: 15, color: "var(--text)" }}>{authorName}</span>
          <span style={{ fontSize: 14, color: "var(--text-muted)" }}>@{authorHandle}</span>
          {hasPersona && card.post_style && (
            <span style={{
              marginLeft: "auto", fontSize: 11, fontWeight: 600,
              color: authorColor, background: avatarBg, padding: "2px 8px", borderRadius: 99,
            }}>
              {POST_STYLE_LABEL[card.post_style] ?? card.post_style}
            </span>
          )}
        </div>

        {/* Subject line: what this post is about */}
        {hasPersona && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, margin: "2px 0 8px", fontSize: 13, color: "var(--text-muted)" }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: topicHue, flexShrink: 0 }} />
            <span>posting about <span style={{ color: "var(--text)", fontWeight: 600 }}>{conceptName}</span> · #{card.topic}</span>
          </div>
        )}

        {/* Body (per-style for persona posts; simple for legacy cards) */}
        {hasPersona ? (
          <PostBody card={card} />
        ) : (
          <>
            <p style={{ margin: "0 0 6px", fontSize: 15, lineHeight: 1.5, color: "var(--text)", fontWeight: 500 }}>{card.hook}</p>
            <p style={{ margin: "0 0 14px", fontSize: 14, lineHeight: 1.65, color: "var(--text-muted)" }}>{card.body}</p>
          </>
        )}

        {/* Engagement row */}
        <div style={{ display: "flex", justifyContent: "space-between", maxWidth: 360 }}>
          <EngageBtn icon={MessageCircle} label="Reply" />
          <EngageBtn icon={Repeat2} label="Repost" />
          <EngageBtn icon={Heart} label="Good post (thumbs up)" onClick={handleUp} active={vote === "up"} activeColor="#f91880" />
          <EngageBtn icon={ThumbsDown} label="Bad post (thumbs down)" onClick={handleDown} active={vote === "down"} activeColor="var(--text-muted)" />
          <EngageBtn icon={Bookmark} label="Bookmark" />
          <EngageBtn icon={Share2} label="Share" />
        </div>

        {/* Optional comment box on thumbs-down */}
        {showComment && (
          <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center" }}>
            <input
              value={comment}
              onChange={e => setComment(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") submitComment(); }}
              placeholder="what missed? (optional)"
              maxLength={280}
              autoFocus
              style={{
                flex: 1, background: "var(--surface-2)", border: "1px solid var(--border)",
                borderRadius: 8, padding: "6px 10px", fontSize: 13, color: "var(--text)", outline: "none",
              }}
            />
            <button
              onClick={submitComment}
              disabled={sending}
              style={{
                background: "var(--surface-2)", border: "1px solid var(--border-strong)",
                borderRadius: 8, padding: "6px 12px", fontSize: 13, fontWeight: 600, color: "var(--text)", cursor: "pointer",
              }}
            >
              Send
            </button>
          </div>
        )}

        {thanks && (
          <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--text-muted)" }}>
            {vote === "up" ? "thanks — noted 🙏" : "thanks for the feedback 🙏"}
          </p>
        )}
      </div>
    </article>
  );
}
