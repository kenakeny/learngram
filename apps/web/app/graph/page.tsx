import { GraphView } from "@/components/graph-view";

interface GraphNode {
  id: string;
  name: string;
  slug: string;
  topic: string;
  depth_level: number;
}

interface GraphEdge {
  from_id: string;
  to_id: string;
  relationship_type: string;
  weight: number;
}

async function getGraph(): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/graph`, { cache: "no-store" });
    if (!res.ok) return { nodes: [], edges: [] };
    return res.json();
  } catch {
    return { nodes: [], edges: [] };
  }
}

export default async function GraphPage() {
  const { nodes, edges } = await getGraph();
  return <GraphView nodes={nodes} edges={edges} />;
}
