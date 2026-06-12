"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

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

const TOPIC_COLOR: Record<string, string> = {
  "networking":           "#3b82f6",
  "caching":              "#f59e0b",
  "databases":            "#10b981",
  "distributed-systems":  "#8b5cf6",
  "consistency":          "#ef4444",
  "messaging":            "#06b6d4",
};

const DEFAULT_COLOR = "#72747f";

function KnowledgeNode({ data }: { data: { label: string; topic: string } }) {
  const color = TOPIC_COLOR[data.topic] ?? DEFAULT_COLOR;
  return (
    <div
      style={{
        background: "#141416",
        border: `1px solid ${color}55`,
        borderLeft: `3px solid ${color}`,
        borderRadius: 8,
        padding: "7px 12px",
        minWidth: 140,
        maxWidth: 200,
        cursor: "default",
      }}
    >
      <Handle type="target" position={Position.Left}  style={{ background: color, border: "none", width: 6, height: 6 }} />
      <div style={{ fontSize: 10, color, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>
        {data.topic}
      </div>
      <div style={{ fontSize: 12, color: "#e8e8ea", lineHeight: 1.35 }}>
        {data.label}
      </div>
      <Handle type="source" position={Position.Right} style={{ background: color, border: "none", width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes: NodeTypes = { knowledge: KnowledgeNode };

const COL_W = 240;
const ROW_H = 90;

function buildLayout(rawNodes: GraphNode[]): Node[] {
  // Group nodes by depth_level, sort within group by topic then name
  const byDepth = new Map<number, GraphNode[]>();
  for (const n of rawNodes) {
    const bucket = byDepth.get(n.depth_level) ?? [];
    bucket.push(n);
    byDepth.set(n.depth_level, bucket);
  }

  const result: Node[] = [];
  for (const [depth, nodes] of byDepth) {
    const sorted = [...nodes].sort((a, b) =>
      a.topic.localeCompare(b.topic) || a.name.localeCompare(b.name)
    );
    sorted.forEach((n, i) => {
      result.push({
        id: n.id,
        type: "knowledge",
        position: { x: (depth - 1) * COL_W, y: i * ROW_H },
        data: { label: n.name, topic: n.topic },
      });
    });
  }
  return result;
}

export function GraphView({ nodes: rawNodes, edges: rawEdges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const nodes = useMemo(() => buildLayout(rawNodes), [rawNodes]);

  const edges: Edge[] = useMemo(
    () =>
      rawEdges.map((e, i) => ({
        id: `e-${i}`,
        source: e.from_id,
        target: e.to_id,
        label: e.relationship_type.replace(/_/g, " "),
        labelStyle: { fill: "#72747f", fontSize: 10 },
        labelBgStyle: { fill: "#141416", fillOpacity: 0.85 },
        style: { stroke: "#3e404a", strokeWidth: 1.5 },
        animated: false,
      })),
    [rawEdges]
  );

  if (rawNodes.length === 0) {
    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "#72747f" }}>
        <span style={{ fontSize: 32 }}>🕸️</span>
        <p style={{ fontSize: 13, margin: 0 }}>No nodes yet — run <code>uv run extract</code> then <code>uv run review</code></p>
      </div>
    );
  }

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        style={{ background: "#0d0d0f" }}
      >
        <Background color="#1a1a1d" gap={24} size={1} />
        <Controls
          style={{ background: "#141416", border: "1px solid rgba(255,255,255,0.07)" }}
        />
        <MiniMap
          style={{ background: "#141416", border: "1px solid rgba(255,255,255,0.07)" }}
          nodeColor={(n) => TOPIC_COLOR[(n.data as { topic: string }).topic] ?? DEFAULT_COLOR}
          maskColor="rgba(13,13,15,0.7)"
        />
      </ReactFlow>

      {/* Topic legend */}
      <div style={{
        position: "absolute", top: 12, right: 12, zIndex: 10,
        background: "#141416", border: "1px solid rgba(255,255,255,0.07)",
        borderRadius: 10, padding: "10px 14px", display: "flex", flexDirection: "column", gap: 6,
      }}>
        {Object.entries(TOPIC_COLOR).map(([topic, color]) => (
          <div key={topic} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: "#72747f", textTransform: "capitalize" }}>
              {topic.replace(/-/g, " ")}
            </span>
          </div>
        ))}
        <div style={{ marginTop: 4, fontSize: 10, color: "#3e404a" }}>
          {rawNodes.length} nodes · {rawEdges.length} edges
        </div>
      </div>
    </div>
  );
}
