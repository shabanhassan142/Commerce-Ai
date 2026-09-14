// src/components/ui/Badge.tsx
// Status and priority color badges

import { cn } from "../../utils/cn";

type BadgeVariant =
  | "default"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "muted";

const VARIANTS: Record<BadgeVariant, string> = {
  default: "bg-primary-500/15 text-primary-300 border-primary-500/25",
  success: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
  warning: "bg-amber-500/15 text-amber-300 border-amber-500/25",
  danger:  "bg-red-500/15 text-red-300 border-red-500/25",
  info:    "bg-sky-500/15 text-sky-300 border-sky-500/25",
  muted:   "bg-white/5 text-[#8888aa] border-white/10",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  dot?: boolean;
}

export function Badge({ children, variant = "default", className, dot }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border",
        VARIANTS[variant],
        className
      )}
    >
      {dot && (
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
      )}
      {children}
    </span>
  );
}

// ── Status mappings ────────────────────────────────────────────────────────────
export function getStatusVariant(status: string): BadgeVariant {
  const s = status?.toLowerCase().replace(/_/g, " ");
  if (s === "open" || s === "reopened") return "info";
  if (s === "assigned") return "default";
  if (s === "in progress" || s === "in_progress") return "warning";
  if (s === "waiting for customer" || s === "waiting") return "muted";
  if (s === "resolved") return "success";
  if (s === "closed") return "muted";
  if (s === "delivered") return "success";
  if (s === "shipped" || s === "processing" || s === "confirmed") return "info";
  if (s === "pending") return "warning";
  if (s === "cancelled" || s === "refunded") return "danger";
  return "muted";
}

export function getPriorityVariant(priority: string): BadgeVariant {
  switch (priority?.toLowerCase()) {
    case "urgent": return "danger";
    case "high":   return "warning";
    case "medium": return "info";
    case "low":    return "muted";
    default:       return "muted";
  }
}

export function StatusBadge({ status }: { status: string }) {
  const label = status?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return <Badge variant={getStatusVariant(status)} dot>{label}</Badge>;
}

export function PriorityBadge({ priority }: { priority: string }) {
  return (
    <Badge variant={getPriorityVariant(priority)}>
      {priority?.toUpperCase()}
    </Badge>
  );
}
