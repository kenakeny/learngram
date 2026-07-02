import { type CardData } from "@/components/feed-card";
import { TopicTabs } from "@/components/topic-tabs";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface TopicCount {
  topic: string;
  cards: number;
  nodes: number;
}

async function getFeed(): Promise<CardData[]> {
  try {
    const res = await fetch(`${API}/feed?limit=20`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.cards ?? [];
  } catch {
    return [];
  }
}

async function getTopics(): Promise<TopicCount[]> {
  try {
    const res = await fetch(`${API}/topics`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export default async function Home() {
  const [cards, topics] = await Promise.all([getFeed(), getTopics()]);

  return <TopicTabs initialCards={cards} initialTopics={topics} />;
}
