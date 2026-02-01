import React from "react";
import StatusBadge from "./StatusBadge";
import SalaryCell from "./SalaryCell";
import type { Job, JobStatus } from "../types/api";

export default function JobRow({ job, companyName, onStatusChange }: { job: Job; companyName?: string; onStatusChange: (id: string, status: JobStatus) => void }) {
  return (
    <tr>
      <td>
        <a className="link" href={job.url} target="_blank" rel="noreferrer">
          {job.title}
        </a>
        <div style={{ color: "#6b7280", fontSize: 12 }}>{companyName || job.company_id}</div>
      </td>
      <td>{job.location || "—"}</td>
      <td>{job.work_mode || "—"}</td>
      <td>{Math.round((job.match_score || 0) * 100)}%</td>
      <td>
        <SalaryCell job={job} />
      </td>
      <td>
        <StatusBadge status={job.status} />
      </td>
      <td>
        <div className="row-actions">
          <button className="button" onClick={() => onStatusChange(job.id, "bookmarked")}>Bookmark</button>
          <button className="button" onClick={() => onStatusChange(job.id, "applied")}>Applied</button>
          <button className="button" onClick={() => onStatusChange(job.id, "hidden")}>Hide</button>
        </div>
      </td>
    </tr>
  );
}
