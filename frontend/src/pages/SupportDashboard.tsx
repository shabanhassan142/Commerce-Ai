// src/pages/SupportDashboard.tsx
// Support agent dashboard — live queue, stats, priority view

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Ticket,
  TrendingUp,
  Zap,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PriorityBadge, StatusBadge } from "../components/ui/Badge";
import { ErrorState } from "../components/ui/ErrorState";
import { SkeletonCard, SkeletonTable } from "../components/ui/Skeleton";
import dashboardService from "../services/dashboard.service";
import ticketsService from "../services/tickets.service";
import { stagger, staggerItem } from "../animations/variants";

function StatCard({ icon: Icon, label, value, color = "primary", sub }: {
  icon: React.ElementType; label: string; value: string | number; color?: string; sub?: string;
}) {
  const c: Record<string, string> = {
    primary: "bg-primary-500/10 text-primary-400 border-primary-500/20",
    emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    amber:   "bg-amber-500/10  text-amber-400  border-amber-500/20",
    red:     "bg-red-500/10    text-red-400    border-red-500/20",
    sky:     "bg-sky-500/10    text-sky-400    border-sky-500/20",
  };
  return (
    <div className="card p-5">
      <div className={`w-9 h-9 rounded-xl border flex items-center justify-center mb-3 ${c[color]}`}>
        <Icon size={16} />
      </div>
      <p className="text-2xl font-bold text-[color:var(--color-text)]">{value}</p>
      <p className="text-xs text-[#8888aa] mt-0.5">{label}</p>
      {sub && <p className="text-xs text-[#6688aa] mt-1">{sub}</p>}
    </div>
  );
}

function fmtSecs(s?: number | null) {
  if (!s) return "—";
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  return `${(s / 3600).toFixed(1)}h`;
}

function slaStatus(deadline?: string) {
  if (!deadline) return null;
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff < 0) return <span className="text-xs text-red-400 font-medium">⚠ Overdue</span>;
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  const color = diff < 3600000 ? "text-red-400" : diff < 7200000 ? "text-amber-400" : "text-emerald-400";
  return <span className={`text-xs font-medium ${color}`}>{h}h {m}m</span>;
}

export default function SupportDashboard() {
  const { data: stats, isLoading: statsLoading, isError: statsError, refetch: refetchStats } = useQuery({
    queryKey: ["support-stats"],
    queryFn: () => dashboardService.getSupportStats(),
    refetchInterval: 30_000,
  });

  const { data: openTickets, isLoading: ticketsLoading } = useQuery({
    queryKey: ["open-tickets", { page: 1, per_page: 10 }],
    queryFn: () => ticketsService.listOpen({ page: 1, per_page: 10 }),
    refetchInterval: 30_000,
  });

  const { data: myTickets } = useQuery({
    queryKey: ["assigned-me", { page: 1 }],
    queryFn: () => ticketsService.listAssignedToMe({ page: 1, per_page: 5 }),
  });

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Header */}
      <motion.div variants={staggerItem}>
        <h1 className="text-2xl font-bold text-[color:var(--color-text)]">Support Dashboard</h1>
        <p className="text-[#8888aa] text-sm mt-0.5">Live ticket queue · refreshes every 30s</p>
      </motion.div>

      {/* Stats row */}
      {statsError ? (
        <ErrorState message="Couldn't load stats." onRetry={refetchStats} />
      ) : (
        <motion.div variants={staggerItem} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statsLoading ? (
            Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)
          ) : (
            <>
              <StatCard icon={Ticket}        label="Open"             value={stats?.open_tickets ?? "—"}           color="sky" />
              <StatCard icon={Clock}         label="Assigned"         value={stats?.assigned_tickets ?? "—"}       color="primary" />
              <StatCard icon={AlertTriangle} label="Urgent"           value={stats?.urgent_tickets ?? "—"}         color="red" />
              <StatCard icon={CheckCircle}   label="Resolved Today"   value={stats?.resolved_today ?? "—"}         color="emerald" />
              <StatCard icon={TrendingUp}    label="AI Resolution"    value={stats?.ai_resolution_percent != null ? `${stats.ai_resolution_percent.toFixed(1)}%` : "—"} color="primary" />
              <StatCard icon={Clock}         label="Avg Response"     value={fmtSecs(stats?.average_response_time_seconds)}    color="sky" />
              <StatCard icon={Clock}         label="Avg Resolution"   value={fmtSecs(stats?.average_resolution_time_seconds)}  color="amber" />
              <StatCard icon={Zap}           label="Escalations"      value={stats?.escalations ?? "—"}            color="amber" />
            </>
          )}
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Open queue */}
        <motion.div variants={staggerItem} className="lg:col-span-2 card overflow-hidden">
          <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[color:var(--color-text)]">Open Queue</h2>
            <Link to="/support/tickets" className="text-xs text-primary-400 hover:text-primary-300">All tickets →</Link>
          </div>
          {ticketsLoading ? (
            <div className="p-5"><SkeletonTable rows={5} /></div>
          ) : openTickets?.items.length === 0 ? (
            <p className="p-8 text-center text-sm text-[#8888aa]">No open tickets 🎉</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5 text-left">
                    {["Ticket", "Subject", "Priority", "SLA", ""].map((h) => (
                      <th key={h} className="px-4 py-2.5 text-[10px] font-semibold text-[#8888aa] uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {openTickets?.items.map((t) => (
                    <tr key={t.id} className="hover:bg-white/3 transition-colors">
                      <td className="px-4 py-2.5 font-mono text-xs text-[#8888aa]">{t.ticket_number}</td>
                      <td className="px-4 py-2.5 text-[color:var(--color-text)] max-w-[200px] truncate">{t.subject}</td>
                      <td className="px-4 py-2.5"><PriorityBadge priority={t.priority} /></td>
                      <td className="px-4 py-2.5">{slaStatus(t.sla_deadline)}</td>
                      <td className="px-4 py-2.5">
                        <Link to={`/support/tickets/${t.id}`} className="text-primary-400 hover:text-primary-300 text-xs">Open →</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>

        {/* My assigned */}
        <motion.div variants={staggerItem} className="card overflow-hidden">
          <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[color:var(--color-text)]">My Queue</h2>
            <Link to="/support/queue" className="text-xs text-primary-400 hover:text-primary-300">View all →</Link>
          </div>
          {myTickets?.items.length === 0 ? (
            <p className="p-8 text-center text-sm text-[#8888aa]">No assigned tickets</p>
          ) : (
            <div className="divide-y divide-white/5">
              {myTickets?.items.map((t) => (
                <Link
                  key={t.id}
                  to={`/support/tickets/${t.id}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-white/3 transition-colors gap-3"
                >
                  <div className="min-w-0">
                    <p className="text-xs text-[#8888aa] font-mono">{t.ticket_number}</p>
                    <p className="text-sm text-[color:var(--color-text)] truncate">{t.subject}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <StatusBadge status={t.status} />
                    {slaStatus(t.sla_deadline)}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}
