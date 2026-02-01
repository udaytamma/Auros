import React from "react";

export default function LineChart({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data || {}).sort((a, b) => a[0].localeCompare(b[0]));
  const max = Math.max(...entries.map(([, v]) => v), 1);

  if (entries.length === 0) {
    return <div className="chart card"><svg viewBox="0 0 400 180" /></div>;
  }

  if (entries.length === 1) {
    const [label, value] = entries[0];
    const y = 160 - (value / max) * 140;
    return (
      <div className="chart card">
        <svg viewBox="0 0 400 180" preserveAspectRatio="none">
          <circle cx="200" cy={y} r="6" fill="#111827" />
          <text x="200" y="175" fontSize="10" fill="#6b7280" textAnchor="middle">{label}</text>
        </svg>
      </div>
    );
  }

  const points = entries.map(([, v], i) => {
    const x = 20 + (i * 360) / (entries.length - 1);
    const y = 160 - (v / max) * 140;
    return `${x},${y}`;
  });

  return (
    <div className="chart card">
      <svg viewBox="0 0 400 180" preserveAspectRatio="none">
        <polyline
          fill="none"
          stroke="#111827"
          strokeWidth="2"
          points={points.join(" ")}
        />
      </svg>
    </div>
  );
}
