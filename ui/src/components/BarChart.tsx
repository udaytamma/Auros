import React from "react";

export default function BarChart({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data || {});
  const max = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div className="chart card">
      <svg viewBox="0 0 400 180" preserveAspectRatio="none">
        {entries.map(([label, value], i) => {
          const barHeight = (value / max) * 140;
          const x = 20 + i * (360 / entries.length);
          const y = 160 - barHeight;
          const width = Math.max(12, 300 / entries.length);
          return (
            <g key={label}>
              <rect x={x} y={y} width={width} height={barHeight} fill="#111827" opacity="0.8" />
              <text x={x} y={170} fontSize="10" fill="#6b7280" transform={`rotate(30 ${x},170)`}>
                {label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
