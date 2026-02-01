import React, { useEffect, useState, useCallback } from "react";
import { fetchCompanies, fetchStats, triggerScan, updateJobStatus, ApiError } from "../api/client";
import { useJobs } from "../hooks/useJobs";
import FilterBar from "../components/FilterBar";
import JobTable from "../components/JobTable";
import BarChart from "../components/BarChart";
import LineChart from "../components/LineChart";
import ScanProgress from "../components/ScanProgress";
import type { Company, StatsResponse, JobStatus, JobFilters } from "../types/api";

export default function Dashboard() {
  const [filters, setFilters] = useState<JobFilters>({ status: "", company_id: "", min_score: "0.7", query: "" });
  const [refreshKey, setRefreshKey] = useState(0);
  const { jobs, loading, error: jobsError } = useJobs(
    {
      status: filters.status,
      company_id: filters.company_id,
      min_score: filters.min_score,
      query: filters.query,
    },
    refreshKey
  );
  const [companies, setCompanies] = useState<Company[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const companyMap = companies.reduce((acc, c) => {
    acc[c.id] = c.name;
    return acc;
  }, {} as Record<string, string>);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [companiesData, statsData] = await Promise.all([fetchCompanies(), fetchStats()]);
        if (!mounted) return;
        setCompanies(companiesData);
        setStats(statsData);
      } catch (err) {
        if (mounted && err instanceof ApiError) setApiError(err);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const handleStatusChange = async (id: string, status: JobStatus) => {
    await updateJobStatus(id, status);
    const refreshed = await fetchStats();
    setStats(refreshed);
    setRefreshKey((k) => k + 1);
  };

  const handleTriggerScan = async () => {
    await triggerScan();
  };

  const handleScanComplete = useCallback(async () => {
    const refreshed = await fetchStats();
    setStats(refreshed);
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="app">
      {(apiError || jobsError) && (
        <div className="card" style={{ borderColor: "#d16b6b", color: "#d16b6b" }}>
          {apiError?.status === 401 || jobsError?.status === 401
            ? "API key required. Set VITE_API_KEY in ui/.env and rebuild the UI."
            : "API error. Check server logs and network connectivity."}
        </div>
      )}
      <div className="header">
        <div>
          <h1>Auros</h1>
          <p>AI-powered job search for Principal TPM/PM roles</p>
        </div>
        <button className="button primary" onClick={handleTriggerScan}>
          Manual Scan
        </button>
      </div>

      <ScanProgress companies={companies} onScanComplete={handleScanComplete} />

      {stats && (
        <div className="grid">
          <div className="stat">
            <h3>Total Jobs</h3>
            <div className="value">{stats.total_jobs}</div>
          </div>
          <div className="stat">
            <h3>New</h3>
            <div className="value">{stats.new_jobs}</div>
          </div>
          <div className="stat">
            <h3>Bookmarked</h3>
            <div className="value">{stats.bookmarked}</div>
          </div>
          <div className="stat">
            <h3>Applied</h3>
            <div className="value">{stats.applied}</div>
          </div>
          <div className="stat">
            <h3>Hidden</h3>
            <div className="value">{stats.hidden}</div>
          </div>
        </div>
      )}

      <div className="grid" style={{ marginTop: 16 }}>
        {stats && <BarChart data={stats.by_company} />}
        {stats && <BarChart data={stats.score_buckets} />}
        {stats && <LineChart data={stats.new_jobs_by_day} />}
      </div>

      <FilterBar filters={filters} companies={companies} onChange={setFilters} />

      {loading ? (
        <div className="card">Loading...</div>
      ) : (
        <JobTable jobs={jobs} companyMap={companyMap} onStatusChange={handleStatusChange} />
      )}
    </div>
  );
}
