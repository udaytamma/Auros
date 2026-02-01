import React from "react";
import JobRow from "./JobRow";
import type { Job, JobStatus } from "../types/api";

export default function JobTable({ jobs, companyMap, onStatusChange }: { jobs: Job[]; companyMap: Record<string, string>; onStatusChange: (id: string, status: JobStatus) => void }) {
  return (
    <div className="card">
      <table className="table">
        <thead>
          <tr>
            <th>Role</th>
            <th>Location</th>
            <th>Mode</th>
            <th>Score</th>
            <th>Salary</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <JobRow
              key={job.id}
              job={job}
              companyName={companyMap[job.company_id]}
              onStatusChange={onStatusChange}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
