// src/components/ui/index.jsx
import React from "react";
import { Loader2, AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { statusDot, statusColor } from "../../utils/helpers";

// ─── Card ─────────────────────────────────────────────────────────────────────

export function Card({ children, className = "", glow = false }) {
  return (
    <div
      className={`glass rounded-xl p-5 ${
        glow ? "shadow-acid" : "shadow-glass"
      } ${className}`}
    >
      {children}
    </div>
  );
}

// ─── Button ───────────────────────────────────────────────────────────────────

export const Button = React.forwardRef(({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled = false,
  loading = false,
  className = "",
  type = "button",
  icon,
  ...props
}, ref) => {
  const base =
    "inline-flex items-center gap-2 font-mono font-medium rounded-lg transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed";

  const variants = {
    primary:
      "bg-acid text-ink-950 hover:bg-acid-dim shadow-acid hover:shadow-none",
    secondary:
      "bg-ink-700 text-frost border border-ink-500 hover:border-acid/30 hover:text-acid",
    ghost: "text-frost-dim hover:text-frost hover:bg-ink-700",
    danger: "bg-danger/10 text-danger border border-danger/20 hover:bg-danger/20",
    plasma: "bg-plasma-light/10 text-plasma-light border border-plasma/20 hover:bg-plasma-light/20",
  };

  const sizes = {
    sm: "text-xs px-3 py-1.5",
    md: "text-sm px-4 py-2",
    lg: "text-base px-6 py-3",
  };

  return (
    <button
      ref={ref}
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 size={14} className="animate-spin" />
      ) : icon ? (
        icon
      ) : null}
      {children}
    </button>
  );
});

Button.displayName = "Button";

// ─── Input ────────────────────────────────────────────────────────────────────

export const Input = React.forwardRef(({ className = "", ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={`w-full bg-ink-800 border border-ink-600 text-frost placeholder-frost-dim font-mono text-sm rounded-lg px-4 py-2.5 focus:outline-none focus:border-acid/40 focus:ring-1 focus:ring-acid/20 transition-all ${className}`}
      {...props}
    />
  );
});

Input.displayName = "Input";

// ─── Textarea ─────────────────────────────────────────────────────────────────

export const Textarea = React.forwardRef(({ className = "", ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={`w-full bg-ink-800 border border-ink-600 text-frost placeholder-frost-dim font-mono text-sm rounded-lg px-4 py-3 focus:outline-none focus:border-acid/40 focus:ring-1 focus:ring-acid/20 transition-all resize-none ${className}`}
      {...props}
    />
  );
});

Textarea.displayName = "Textarea";

// ─── Select ───────────────────────────────────────────────────────────────────

export const Select = React.forwardRef(({ children, className = "", ...props }, ref) => {
  return (
    <select
      ref={ref}
      className={`bg-ink-800 border border-ink-600 text-frost font-mono text-sm rounded-lg px-3 py-2.5 focus:outline-none focus:border-acid/40 transition-all cursor-pointer ${className}`}
      {...props}
    >
      {children}
    </select>
  );
});

Select.displayName = "Select";

// ─── Badge ────────────────────────────────────────────────────────────────────

export function Badge({ children, variant = "default", className = "" }) {
  const variants = {
    default: "bg-ink-700 text-frost-dim",
    acid: "bg-acid-muted text-acid border border-acid/20",
    plasma: "bg-plasma-muted text-plasma-light border border-plasma/20",
    signal: "bg-signal-muted text-signal border border-signal/20",
    danger: "bg-red-500/10 text-danger border border-danger/20",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded-md ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

export function StatusBadge({ status }) {
  const variantMap = {
    ready: "acid",
    processing: "signal",
    indexing: "plasma",
    failed: "danger",
    pending: "default",
  };
  return (
    <Badge variant={variantMap[status?.toLowerCase()] || "default"}>
      <span className={`w-1.5 h-1.5 rounded-full ${statusDot(status)} inline-block`} />
      {status}
    </Badge>
  );
}

// ─── Loading Spinner ─────────────────────────────────────────────────────────

export function Spinner({ size = 20 }) {
  return (
    <Loader2
      size={size}
      className="animate-spin text-acid"
    />
  );
}

// ─── Empty State ─────────────────────────────────────────────────────────────

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      {Icon && (
        <div className="w-16 h-16 rounded-2xl bg-ink-800 border border-ink-600 flex items-center justify-center mb-4">
          <Icon size={28} className="text-frost-dim" />
        </div>
      )}
      <h3 className="font-display text-frost font-bold mb-2">{title}</h3>
      <p className="text-frost-dim text-sm font-body max-w-xs mb-6">{description}</p>
      {action}
    </div>
  );
}

// ─── Error Alert ─────────────────────────────────────────────────────────────

export function ErrorAlert({ message, onRetry }) {
  return (
    <div className="flex items-start gap-3 bg-danger/5 border border-danger/20 rounded-xl p-4">
      <XCircle size={18} className="text-danger mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-danger font-mono">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-xs text-danger/70 hover:text-danger underline mt-1 font-mono"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Section Header ───────────────────────────────────────────────────────────

export function SectionHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-frost tracking-tight">
          {title}
        </h1>
        {subtitle && (
          <p className="text-frost-dim text-sm font-body mt-1">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

// ─── Skeleton Loader ──────────────────────────────────────────────────────────

export function Skeleton({ className = "" }) {
  return (
    <div className={`shimmer rounded-lg ${className}`} />
  );
}

// ─── Score Bar ────────────────────────────────────────────────────────────────

export function ScoreBar({ score }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? "bg-acid" : pct >= 60 ? "bg-signal" : "bg-plasma-light";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-ink-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-frost-dim w-8 text-right">
        {pct}%
      </span>
    </div>
  );
}

// ─── Tabs ────────────────────────────────────────────────────────────────────

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 bg-ink-800 rounded-lg p-1 border border-ink-600">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={`flex-1 text-xs font-mono py-1.5 px-3 rounded-md transition-all ${
            active === tab.value
              ? "bg-acid text-ink-950 font-bold"
              : "text-frost-dim hover:text-frost"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
