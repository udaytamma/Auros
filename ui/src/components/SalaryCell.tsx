import React from "react";
import type { Job } from "../types/api";

export default function SalaryCell({ job }: { job: Job }) {
  if (!job.salary_min || !job.salary_max) return <span>—</span>;
  const label = `$${Math.round(job.salary_min / 1000)}k - $${Math.round(job.salary_max / 1000)}k`;

  const sourceLabel = job.salary_source === "jd" ? "from JD" : job.salary_source === "ai" ? "AI est." : "";

  return (
    <span>
      {label}
      {sourceLabel && <span style={{ color: "#6b7280", fontSize: 11, marginLeft: 4 }}>({sourceLabel})</span>}
    </span>
  );
}
