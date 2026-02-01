import React, { useEffect, useState, useCallback } from "react";
import { fetchScanStatus, stopScan } from "../api/client";
import type { ScanStatusResponse, Company } from "../types/api";

interface ScanProgressProps {
  companies: Company[];
  onScanComplete?: () => void;
}

function formatElapsedTime(startedAt: string | null): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const now = Date.now();
  const elapsed = Math.floor((now - start) / 1000);

  const hours = Math.floor(elapsed / 3600);
  const minutes = Math.floor((elapsed % 3600) / 60);
  const seconds = elapsed % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function ScanProgress({ companies, onScanComplete }: ScanProgressProps) {
  const [status, setStatus] = useState<ScanStatusResponse | null>(null);
  const [elapsedDisplay, setElapsedDisplay] = useState("—");
  const [wasRunning, setWasRunning] = useState(false);
  const [stopping, setStopping] = useState(false);

  const totalCompanies = companies.filter(c => c.enabled).length;

  const handleStop = async () => {
    setStopping(true);
    try {
      await stopScan();
      setWasRunning(false);
    } catch (e) {
      console.error("Failed to stop scan", e);
    } finally {
      setStopping(false);
    }
  };

  const poll = useCallback(async () => {
    try {
      const data = await fetchScanStatus();
      setStatus(data);

      if (data.status === "running") {
        setWasRunning(true);
        setElapsedDisplay(formatElapsedTime(data.started_at));
      } else if (wasRunning) {
        setWasRunning(false);
        onScanComplete?.();
      }
    } catch (e) {
      console.error("Failed to fetch scan status", e);
    }
  }, [wasRunning, onScanComplete]);

  // Poll every 2 seconds when running, every 10 seconds when idle
  useEffect(() => {
    poll();
    const interval = setInterval(poll, status?.status === "running" ? 2000 : 10000);
    return () => clearInterval(interval);
  }, [poll, status?.status]);

  // Update elapsed time display every second when running
  useEffect(() => {
    if (status?.status !== "running") return;
    const timer = setInterval(() => {
      setElapsedDisplay(formatElapsedTime(status.started_at));
    }, 1000);
    return () => clearInterval(timer);
  }, [status?.status, status?.started_at]);

  const isRunning = status?.status === "running";
  const isIdle = status?.status === "idle";
  const isCompleted = status?.status === "completed";
  const progress = totalCompanies > 0 ? (status?.companies_scanned || 0) / totalCompanies : 0;

  return (
    <div className={`scan-progress ${isRunning ? "scan-progress--active" : ""}`}>
      <div className="scan-progress__header">
        <div className="scan-progress__title">
          <div className={`scan-progress__indicator ${isRunning ? "scan-progress__indicator--pulse" : ""}`} />
          <span className="scan-progress__label">
            {isRunning ? "Scanning" : isCompleted ? "Last Scan" : "Scanner Idle"}
          </span>
        </div>
        <div className="scan-progress__actions">
          {status?.started_at && (
            <div className="scan-progress__time">
              Started {formatTime(status.started_at)}
            </div>
          )}
          {isRunning && (
            <button
              className="button button--stop"
              onClick={handleStop}
              disabled={stopping}
            >
              {stopping ? "Stopping..." : "Stop Scan"}
            </button>
          )}
        </div>
      </div>

      {(isRunning || isCompleted) && (
        <>
          <div className="scan-progress__metrics">
            <div className="scan-progress__metric">
              <span className="scan-progress__metric-value">{elapsedDisplay}</span>
              <span className="scan-progress__metric-label">Elapsed</span>
            </div>
            <div className="scan-progress__metric">
              <span className="scan-progress__metric-value">
                {status?.companies_scanned || 0}
                <span className="scan-progress__metric-total">/{totalCompanies}</span>
              </span>
              <span className="scan-progress__metric-label">Companies</span>
            </div>
            <div className="scan-progress__metric">
              <span className="scan-progress__metric-value">{status?.jobs_found || 0}</span>
              <span className="scan-progress__metric-label">Jobs Found</span>
            </div>
            <div className="scan-progress__metric scan-progress__metric--highlight">
              <span className="scan-progress__metric-value">{status?.jobs_new || 0}</span>
              <span className="scan-progress__metric-label">New Jobs</span>
            </div>
          </div>

          {isRunning && (
            <div className="scan-progress__bar-container">
              <div
                className="scan-progress__bar"
                style={{ width: `${Math.max(progress * 100, 2)}%` }}
              />
            </div>
          )}

          {status?.errors && status.errors.length > 0 && (
            <div className="scan-progress__errors">
              <div className="scan-progress__errors-header">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {status.errors.length} error{status.errors.length > 1 ? "s" : ""} encountered
              </div>
              <ul className="scan-progress__errors-list">
                {status.errors.slice(0, 5).map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
                {status.errors.length > 5 && (
                  <li className="scan-progress__errors-more">
                    +{status.errors.length - 5} more errors
                  </li>
                )}
              </ul>
            </div>
          )}
        </>
      )}

      {isIdle && !status?.started_at && (
        <div className="scan-progress__idle">
          No scans have been run yet. Click "Manual Scan" to start.
        </div>
      )}
    </div>
  );
}
