import React from "react";
import type { Company, JobFilters } from "../types/api";

export default function FilterBar({ filters, companies, onChange }: { filters: JobFilters; companies: Company[]; onChange: (next: JobFilters) => void }) {
  return (
    <div className="filters">
      <input
        type="text"
        placeholder="Search title..."
        value={filters.query || ""}
        onChange={(e) => onChange({ ...filters, query: e.target.value })}
      />
      <select value={filters.company_id || ""} onChange={(e) => onChange({ ...filters, company_id: e.target.value })}>
        <option value="">All companies</option>
        {companies.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <select value={filters.status || ""} onChange={(e) => onChange({ ...filters, status: e.target.value })}>
        <option value="">All status</option>
        <option value="new">New</option>
        <option value="bookmarked">Bookmarked</option>
        <option value="applied">Applied</option>
        <option value="hidden">Hidden</option>
      </select>
      <select value={filters.min_score || ""} onChange={(e) => onChange({ ...filters, min_score: e.target.value })}>
        <option value="">Min score</option>
        <option value="0.5">50%</option>
        <option value="0.7">70%</option>
        <option value="0.8">80%</option>
        <option value="0.9">90%</option>
      </select>
    </div>
  );
}
