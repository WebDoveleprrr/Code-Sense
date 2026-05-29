// src/utils/helpers.js

export function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatMs(ms) {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function statusColor(status) {
  const map = {
    ready: "text-acid",
    processing: "text-signal",
    pending: "text-frost-dim",
    failed: "text-danger",
    indexing: "text-plasma-light",
  };
  return map[status?.toLowerCase()] || "text-frost-dim";
}

export function statusDot(status) {
  const map = {
    ready: "bg-acid",
    processing: "bg-signal animate-pulse",
    pending: "bg-frost-dim",
    failed: "bg-danger",
    indexing: "bg-plasma-light animate-pulse",
  };
  return map[status?.toLowerCase()] || "bg-frost-dim";
}

export function langColor(lang) {
  const map = {
    python: "#3572A5",
    javascript: "#f1e05a",
    typescript: "#3178c6",
    "c++": "#f34b7d",
    java: "#b07219",
    go: "#00ADD8",
    rust: "#dea584",
    ruby: "#701516",
    php: "#4F5D95",
    css: "#563d7c",
    html: "#e34c26",
    shell: "#89e051",
  };
  return map[lang?.toLowerCase()] || "#94a3b8";
}

export function truncate(str, n = 80) {
  if (!str) return "";
  return str.length > n ? str.slice(0, n) + "…" : str;
}

export function timeAgo(isoStr) {
  if (!isoStr) return "";
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
