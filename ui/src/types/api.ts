export interface Company {
  id: string;
  name: string;
  careers_url: string;
  tier: number;
  enabled: boolean;
  last_scraped?: string | null;
  scrape_status?: string | null;
}

export type JobStatus = "new" | "bookmarked" | "applied" | "hidden";
export type WorkMode = "remote" | "hybrid" | "onsite" | "unclear";
export type SalarySource = "jd" | "ai";

export interface Job {
  id: string;
  company_id: string;
  title: string;
  primary_function?: string | null;
  url: string;
  yoe_min?: number | null;
  yoe_max?: number | null;
  yoe_source?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_source?: SalarySource | null;
  salary_confidence?: number | null;
  salary_estimated?: boolean | null;
  work_mode?: WorkMode | null;
  location?: string | null;
  match_score?: number | null;
  raw_description?: string | null;
  status: JobStatus;
  first_seen?: string | null;
  last_seen?: string | null;
  notified: boolean;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
}

export interface StatsResponse {
  total_jobs: number;
  new_jobs: number;
  bookmarked: number;
  applied: number;
  hidden: number;
  last_scan?: string | null;
  by_company: Record<string, number>;
  score_buckets: Record<string, number>;
  new_jobs_by_day: Record<string, number>;
}

export interface JobFilters {
  status: string;
  company_id: string;
  min_score: string;
  query: string;
}

export interface ScanStatusResponse {
  status: "idle" | "running" | "completed";
  started_at: string | null;
  completed_at: string | null;
  companies_scanned: number;
  jobs_found: number;
  jobs_new: number;
  errors: string[];
}
