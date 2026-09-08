"use client";

import { TopologyEdge, TopologyNode } from "@/lib/types";

const ICONS: Record<string, string> = {
  pc: "🖥️",
  switch: "🔀",
  router: "📡",
  server: "🗄️",
};

const TYPE_FILL: Record<string, string> = {
  pc: "#60a5fa",
  switch: "#2dd4bf",
  router: "#fbbf24",
  server: "#4ade80",
};

interface Props {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  selectedDevice: string | null;
  onSelectDevice: (id: string) => void;
}

/**
 * Simple deterministic horizontal-flow layout: devices are placed left to
 * right in the order they appear in `nodes`. This intentionally avoids a
 * heavyweight graph-layout dependency — the MVP's topologies are all
 * small linear chains, so a manual layout stays legible and dependency-free.
 */
export default function TopologyDiagram({ nodes, edges, selectedDevice, onSelectDevice }: Props) {
  const spacingX = 160;
  const y = 90;
  const positions: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n, i) => {
    positions[n.id] = { x: 60 + i * spacingX, y };
  });

  const width = 60 + Math.max(0, nodes.length - 1) * spacingX + 60;

  return (
    <div className="overflow-x-auto rounded-lg border border-ink-700 bg-ink-900 p-4">
      <svg width={Math.max(width, 320)} height="200" className="mx-auto">
        {edges.map((edge, i) => {
          const a = positions[edge.from];
          const b = positions[edge.to];
          if (!a || !b) return null;
          return (
            <g key={i}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#28345a" strokeWidth={2} />
              <text x={(a.x + b.x) / 2} y={a.y - 26} textAnchor="middle" className="fill-slate-500" fontSize={9}>
                {edge.from_if}
              </text>
              <text x={(a.x + b.x) / 2} y={a.y + 34} textAnchor="middle" className="fill-slate-500" fontSize={9}>
                {edge.to_if}
              </text>
            </g>
          );
        })}

        {nodes.map((node) => {
          const pos = positions[node.id];
          const selected = selectedDevice === node.id;
          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={() => onSelectDevice(node.id)}
              className="cursor-pointer"
            >
              <rect
                x={-42}
                y={-32}
                width={84}
                height={64}
                rx={10}
                stroke={selected ? "#5eead4" : "#28345a"}
                strokeWidth={selected ? 2 : 1}
                fill={TYPE_FILL[node.type] || "#28345a"}
                fillOpacity={0.12}
              />
              <text x={0} y={-4} textAnchor="middle" fontSize={20}>
                {ICONS[node.type] || "❓"}
              </text>
              <text x={0} y={16} textAnchor="middle" fontSize={11} className="fill-slate-200 font-medium">
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="mt-2 text-center text-xs text-slate-500">Click a device to target it in the CLI below.</p>
    </div>
  );
}
