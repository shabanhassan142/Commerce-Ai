// src/pages/SupportTickets.tsx
// Support agent full ticket queue with filters

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Ticket } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PriorityBadge, StatusBadge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Pagination } from "../components/ui/Pagination";
import { SkeletonTable } from "../components/ui/Skeleton";
import ticketsService from "../services/tickets.service";

const STATUS_TABS = ["", "open", "assigned", "in_progress", "waiting_for_customer", "resolved", "closed"] as const;
const PRIORITY_FILTERS = ["", "urgent", "high", "medium", "low"] as const;

export default function SupportTickets() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");
  const [priority, setPriority] = useState<string>("");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["support-tickets", { page, status, priority }],
    queryFn: () => ticketsService.list({
      page, per_page: 20,
      status: status || undefined,
      priority: priority || undefined,
    }),
  });

  const formatSla = (deadline?: string) => {
    if (!deadline) return "—";
    const diff = new Date(deadline).getTime() - Date.now();
    if (diff < 0) return <span className="text-red-400 text-xs">Overdue</span>;
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    return <span className={`text-xs ${diff < 3600000 ? "text-red-400" : diff < 7200000 ? "text-amber-400" : "text-emerald-400"}`}>{h}h {m}m</span>;
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)]">Ticket Queue</h1>
          <p className="text-[#8888aa] text-sm mt-0.5">{data ? `${data.total} tickets` : "All support tickets"}</p>
        </div>
        <select
          value={priority}
          onChange={(e) => { setPriority(e.target.value); setPage(1); }}
          className="input-field w-auto py-2 text-sm"
          aria-label="Priority filter"
        >
          {PRIORITY_FILTERS.map((p) => (
            <option key={p || "all"} value={p}>{p ? p.charAt(0).toUpperCase() + p.slice(1) : "All Priorities"}</option>
          ))}
        </select>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {STATUS_TABS.map((s) => (
          <button key={s || "all"} onClick={() => { setStatus(s); setPage(1); }}
            className={`flex-shrink-0 px-4 py-1.5 rounded-full text-xs font-medium capitalize transition-colors ${status === s ? "bg-primary-600 text-white" : "bg-white/5 text-[#8888aa] hover:bg-white/10 hover:text-[color:var(--color-text)]"}`}>
            {s.replace(/_/g, " ") || "All"}
          </button>
        ))}
      </div>

      {isError ? (
        <ErrorState message="Couldn't load tickets." onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="card p-5"><SkeletonTable rows={8} /></div>
      ) : data?.items.length === 0 ? (
        <EmptyState icon={Ticket} title="No tickets" description="No tickets match your filters." />
      ) : (
        <>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left">
                  {["Ticket", "Subject", "Priority", "Status", "SLA", "Updated", ""].map(h => (
                    <th key={h} className="px-4 py-3 text-[10px] font-semibold text-[#8888aa] uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {data?.items.map((t) => (
                  <motion.tr key={t.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="hover:bg-white/3 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-[#8888aa]">{t.ticket_number}</td>
                    <td className="px-4 py-3 text-[color:var(--color-text)] max-w-[200px] truncate">{t.subject}</td>
                    <td className="px-4 py-3"><PriorityBadge priority={t.priority} /></td>
                    <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                    <td className="px-4 py-3">{formatSla(t.sla_deadline)}</td>
                    <td className="px-4 py-3 text-xs text-[#8888aa]">{t.updated_at ? new Date(t.updated_at).toLocaleDateString() : "—"}</td>
                    <td className="px-4 py-3">
                      <Link to={`/support/tickets/${t.id}`} className="text-primary-400 hover:text-primary-300 text-xs font-medium">Open →</Link>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
          {data && <Pagination page={data.page} pages={data.pages} total={data.total} perPage={data.per_page} onPageChange={setPage} />}
        </>
      )}
    </div>
  );
}
