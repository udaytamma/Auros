import type { Company, JobListResponse, StatsResponse, Job, ScanStatusResponse } from "../types/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const API_KEY = import.meta.env.VITE_API_KEY || "";

function withAuth(headers: HeadersInit = {}) {
  if (!API_KEY) return headers;
  return { ...headers, "X-API-Key": API_KEY };
}

export async function fetchJobs(params: Record<string, string> = {}): Promise<JobListResponse> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) searchParams.set(key, value);
  });
  const query = searchParams.toString();
  const url = `${API_BASE}/jobs${query ? `?${query}` : ""}`;
  const res = await fetch(url, { headers: withAuth() });
  if (!res.ok) throw new ApiError(res.status, `Failed to fetch jobs (HTTP ${res.status})`);
  return res.json();
}

export async function fetchCompanies(): Promise<Company[]> {
  const res = await fetch(`${API_BASE}/companies`, { headers: withAuth() });
  if (!res.ok) throw new ApiError(res.status, `Failed to fetch companies (HTTP ${res.status})`);
  return res.json();
}

export async function updateJobStatus(jobId: string, status: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/status`, {
    method: "PATCH",
    headers: withAuth({ "Content-Type": "application/json" }),
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new ApiError(res.status, `Failed to update status (HTTP ${res.status})`);
  return res.json();
}

export async function fetchStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/stats`, { headers: withAuth() });
  if (!res.ok) throw new ApiError(res.status, `Failed to fetch stats (HTTP ${res.status})`);
  return res.json();
}

export async function triggerScan(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/search/trigger`, { method: "POST", headers: withAuth() });
  if (!res.ok) throw new ApiError(res.status, `Failed to trigger scan (HTTP ${res.status})`);
  return res.json();
}

export async function fetchScanStatus(): Promise<ScanStatusResponse> {
  const res = await fetch(`${API_BASE}/search/status`, { headers: withAuth() });
  if (!res.ok) throw new ApiError(res.status, `Failed to fetch scan status (HTTP ${res.status})`);
  return res.json();
}

export async function stopScan(): Promise<{ status: string; tasks_cancelled: number }> {
  const res = await fetch(`${API_BASE}/search/stop`, { method: "POST", headers: withAuth() });
  if (!res.ok) throw new ApiError(res.status, `Failed to stop scan (HTTP ${res.status})`);
  return res.json();
}
