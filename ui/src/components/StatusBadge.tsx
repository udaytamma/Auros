import React from "react";

const statusClass = (status: string) => {
  switch (status) {
    case "bookmarked":
      return "badge bookmarked";
    case "applied":
      return "badge applied";
    case "hidden":
      return "badge hidden";
    default:
      return "badge new";
  }
};

export default function StatusBadge({ status }: { status: string }) {
  return <span className={statusClass(status)}>{status}</span>;
}
