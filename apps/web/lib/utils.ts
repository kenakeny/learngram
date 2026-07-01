import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Topics are AI-judged and open-ended. The original six keep their hand-picked
// colors; anything new gets a stable color derived from the topic string.
const KNOWN_TOPIC_COLORS: Record<string, string> = {
  networking: "#6b9ab8",
  caching: "#b89a5a",
  databases: "#5aa87a",
  "distributed-systems": "#9b8fc4",
  consistency: "#c47080",
  messaging: "#5ab0b0",
};

function hashHue(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(h, 31) + s.charCodeAt(i)) | 0;
  return ((h % 360) + 360) % 360;
}

export function topicColor(topic: string): string {
  return KNOWN_TOPIC_COLORS[topic] ?? `hsl(${hashHue(topic)} 42% 62%)`;
}

/** Same color at low opacity, for avatar/badge backgrounds. */
export function topicBg(topic: string, alpha = 0.15): string {
  const c = topicColor(topic);
  if (c.startsWith("#")) {
    return c + Math.round(alpha * 255).toString(16).padStart(2, "0");
  }
  return c.replace(")", ` / ${alpha})`); // hsl(h s l / a)
}

/** Two-letter badge from a topic slug, e.g. "distributed-systems" -> "DS". */
export function topicInitials(topic: string): string {
  const parts = topic.split("-").filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (topic.slice(0, 2) || "SD").toUpperCase();
}
