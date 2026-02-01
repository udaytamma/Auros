import { useEffect, useState, useMemo } from "react";
import { fetchJobs, ApiError } from "../api/client";
import type { Job } from "../types/api";

export function useJobs(filters: Record<string, string>, refreshKey: number) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  // Stable filter key
  const filterKey = useMemo(() =>
    Object.entries(filters).sort().map(([k, v]) => `${k}=${v}`).join("&"),
    [filters.status, filters.company_id, filters.min_score, filters.query]
  );

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    fetchJobs(filters)
      .then((data) => {
        if (mounted) setJobs(data.jobs || []);
      })
      .catch((err) => {
        if (mounted && err instanceof ApiError) setError(err);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [filterKey, refreshKey]);

  return { jobs, loading, error };
}
