// src/pages/TicketWorkspace.tsx
// Professional 3-column Support Agent Ticket Workspace & Helpdesk

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Bot,
  ChevronDown,
  Clock,
  ExternalLink,
  Lock,
  Mail,
  Package,
  RefreshCw,
  Search,
  Send,
  User,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { PriorityBadge, StatusBadge } from "../components/ui/Badge";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import useAuth from "../hooks/useAuth";
import ticketsService from "../services/tickets.service";
import type { TicketPriority, TicketStatus } from "../types";

const STATUSES: TicketStatus[] = [
  "open",
  "assigned",
  "in_progress",
  "waiting_for_customer",
  "resolved",
  "closed",
  "reopened",
];
const PRIORITIES: TicketPriority[] = ["low", "medium", "high", "urgent"];

function slaCountdown(deadline?: string) {
  if (!deadline) return null;
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff < 0) return { label: "⚠ SLA Overdue", color: "text-red-400" };
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return {
    label: `${h}h ${m}m remaining`,
    color: diff < 3600000 ? "text-red-400" : diff < 7200000 ? "text-amber-400" : "text-emerald-400",
  };
}

export default function TicketWorkspace() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const qc = useQueryClient();

  const [replyContent, setReplyContent] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [showNote, setShowNote] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const [search, setSearch] = useState("");

  const { data: ticket, isLoading, isError, refetch } = useQuery({
    queryKey: ["support-ticket", id],
    queryFn: () => ticketsService.getById(id!),
    enabled: !!id,
    refetchInterval: 15_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["support-ticket", id] });

  const assignMutation = useMutation({
    mutationFn: () => ticketsService.assign(id!, { agent_id: user!.id }),
    onSuccess: () => { invalidate(); toast.success("Ticket assigned to you"); },
    onError: () => toast.error("Assignment failed"),
  });

  const unassignMutation = useMutation({
    mutationFn: () => ticketsService.assign(id!, { agent_id: null }),
    onSuccess: () => { invalidate(); toast.success("Ticket unassigned"); },
    onError: () => toast.error("Unassignment failed"),
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => ticketsService.updateStatus(id!, { status }),
    onSuccess: () => { invalidate(); toast.success("Ticket status updated"); },
    onError: () => toast.error("Failed to update status"),
  });

  const priorityMutation = useMutation({
    mutationFn: (priority: string) => ticketsService.updatePriority(id!, { priority }),
    onSuccess: () => { invalidate(); toast.success("Ticket priority updated"); },
    onError: () => toast.error("Failed to update priority"),
  });

  const replyMutation = useMutation({
    mutationFn: (content: string) => ticketsService.reply(id!, { content }),
    onSuccess: () => { invalidate(); setReplyContent(""); toast.success("Reply sent to customer"); },
    onError: () => toast.error("Failed to send reply"),
  });

  const noteMutation = useMutation({
    mutationFn: (content: string) => ticketsService.addNote(id!, { content }),
    onSuccess: () => { invalidate(); setNoteContent(""); setShowNote(false); toast.success("Internal note saved (Private 🔒)"); },
    onError: () => toast.error("Failed to add internal note"),
  });

  if (isError) return <ErrorState message="Ticket not found." onRetry={() => refetch()} type="notfound" />;

  // Build sorted thread of customer/agent replies and internal notes
  const thread = ticket
    ? [
        ...ticket.replies.map((r) => ({ ...r, _type: "reply" as const })),
        ...ticket.notes.map((n) => ({ ...n, _type: "note" as const, author_type: "internal" })),
      ].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    : [];

  const sla = slaCountdown(ticket?.sla_deadline);

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col -m-4 md:-m-6">
      {/* Top Header Bar */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/5 bg-card flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => navigate("/support/tickets")}
            className="text-[#8888aa] hover:text-[color:var(--color-text)] p-1 rounded-lg hover:bg-white/5"
            aria-label="Back"
          >
            <ArrowLeft size={16} />
          </button>
          {ticket && (
            <>
              <span className="text-xs font-mono font-bold text-primary-400">{ticket.ticket_number}</span>
              <h1 className="text-sm font-bold text-[color:var(--color-text)] truncate">{ticket.subject}</h1>
              <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
                <StatusBadge status={ticket.status} />
                <PriorityBadge priority={ticket.priority} />
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {ticket && !ticket.assigned_to && (
            <button
              onClick={() => assignMutation.mutate()}
              disabled={assignMutation.isPending}
              className="btn-primary text-xs py-1.5 px-3"
            >
              Claim Ticket
            </button>
          )}
          <button
            onClick={() => refetch()}
            className="p-1.5 text-[#8888aa] hover:text-[color:var(--color-text)] rounded-lg hover:bg-white/5"
            title="Refresh ticket data"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* 3-Column Workspace Grid */}
      <div className="flex-1 flex overflow-hidden">
        {/* ── Col 1: Ticket Queue & Search Sidebar ── */}
        <div className="hidden lg:flex w-64 flex-col border-r border-white/5 bg-card/50">
          <div className="p-3 border-b border-white/5 space-y-2">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-2.5 text-[#8888aa]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search ticket #, subject..."
                className="w-full bg-white/5 border border-white/10 rounded-lg pl-8 pr-2 py-1.5 text-xs text-[color:var(--color-text)] placeholder-[#666688] focus:outline-none focus:border-primary-500"
              />
            </div>
          </div>
          <OpenTicketList currentId={id} search={search} />
        </div>

        {/* ── Col 2: Main Conversation & Action Area ── */}
        <div className="flex-1 flex flex-col min-w-0 bg-background">
          {isLoading ? (
            <div className="p-6 space-y-4">
              <Skeleton className="h-16" />
              <Skeleton className="h-24" />
              <Skeleton className="h-24" />
            </div>
          ) : ticket ? (
            <>
              {/* Messages Thread Scroll Area */}
              <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
                {/* Original Customer Message */}
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary-500/20 border border-primary-500/30 flex items-center justify-center flex-shrink-0">
                    <User size={14} className="text-primary-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-[color:var(--color-text)]">
                        {ticket.customer_name || "Customer"}
                      </span>
                      <span className="text-[10px] text-[#8888aa]">
                        {new Date(ticket.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="card p-4 rounded-tl-sm bg-white/5 border-white/10">
                      <p className="text-sm text-[color:var(--color-text)] leading-relaxed whitespace-pre-wrap">
                        {ticket.description}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Threaded Replies & Internal Notes */}
                {thread.map((item) => {
                  const isNote = item._type === "note";
                  const isCustomer = !isNote && (item as { author_type: string }).author_type === "customer";
                  return (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex gap-3"
                    >
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          isNote
                            ? "bg-amber-500/20 border border-amber-500/30"
                            : isCustomer
                            ? "bg-primary-500/20 border border-primary-500/30"
                            : "bg-emerald-500/20 border border-emerald-500/30"
                        }`}
                      >
                        {isNote ? (
                          <Lock size={12} className="text-amber-400" />
                        ) : isCustomer ? (
                          <User size={13} className="text-primary-400" />
                        ) : (
                          <span className="text-xs font-bold text-emerald-400">
                            {(item.author_name ?? "A").charAt(0)}
                          </span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="text-xs font-semibold text-[color:var(--color-text)]">
                            {isNote
                              ? `Internal Note (${item.author_name || "Agent"})`
                              : isCustomer
                              ? ticket.customer_name || "Customer"
                              : item.author_name || "Support Agent"}
                          </span>
                          {isNote && (
                            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 uppercase tracking-wide">
                              🔒 Private Note
                            </span>
                          )}
                          <span className="text-[10px] text-[#8888aa]">
                            {new Date(item.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div
                          className={`p-4 rounded-xl text-sm leading-relaxed ${
                            isNote
                              ? "bg-amber-500/10 border border-amber-500/20 text-amber-200"
                              : isCustomer
                              ? "card rounded-tl-sm bg-white/5 border-white/10"
                              : "card rounded-tl-sm bg-emerald-500/5 border-emerald-500/20"
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{item.content}</p>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>

              {/* Bottom Response & Note Controls */}
              <div className="p-4 border-t border-white/5 bg-card/60 space-y-3 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowNote(false)}
                    className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      !showNote ? "bg-primary-600 text-white" : "text-[#8888aa] hover:bg-white/5"
                    }`}
                  >
                    Reply to Customer
                  </button>
                  <button
                    onClick={() => setShowNote(true)}
                    className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      showNote ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" : "text-[#8888aa] hover:bg-white/5"
                    }`}
                  >
                    <Lock size={12} /> Add Internal Note 🔒
                  </button>
                </div>

                {showNote ? (
                  <div className="bg-amber-500/10 border border-amber-500/20 p-3 rounded-xl space-y-2">
                    <p className="text-xs font-semibold text-amber-400 flex items-center gap-1">
                      <Lock size={12} /> INTERNAL NOTE (Hidden from Customer)
                    </p>
                    <textarea
                      value={noteContent}
                      onChange={(e) => setNoteContent(e.target.value)}
                      placeholder="Write an internal note for your support team..."
                      rows={3}
                      className="input-field bg-black/30 border-amber-500/30 text-amber-100 placeholder-amber-500/50 resize-none w-full text-sm"
                    />
                    <div className="flex justify-end">
                      <button
                        onClick={() => noteContent.trim() && noteMutation.mutate(noteContent.trim())}
                        disabled={!noteContent.trim() || noteMutation.isPending}
                        className="btn-primary bg-amber-600 hover:bg-amber-500 text-xs py-2 px-4"
                      >
                        Save Internal Note
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-3 items-end">
                    <textarea
                      value={replyContent}
                      onChange={(e) => setReplyContent(e.target.value)}
                      placeholder="Write a response to the customer..."
                      rows={3}
                      className="flex-1 input-field resize-none text-sm"
                      disabled={replyMutation.isPending}
                    />
                    <button
                      onClick={() => replyContent.trim() && replyMutation.mutate(replyContent.trim())}
                      disabled={!replyContent.trim() || replyMutation.isPending}
                      className="h-10 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 flex items-center gap-2 text-xs font-semibold text-white transition-all flex-shrink-0"
                    >
                      <Send size={14} /> Send Reply
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>

        {/* ── Col 3: Customer & Ticket Context Sidebar ── */}
        <div className="hidden xl:flex w-72 flex-col border-l border-white/5 bg-card/50 overflow-y-auto p-4 space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-8" />
              <Skeleton className="h-24" />
              <Skeleton className="h-24" />
            </div>
          ) : ticket ? (
            <>
              {/* SLA Banner */}
              {sla && (
                <div className="card p-3 bg-white/3 border-white/10">
                  <div className="flex items-center gap-2 mb-1">
                    <Clock size={14} className={sla.color} />
                    <span className="text-xs font-bold text-[color:var(--color-text)]">SLA Target</span>
                  </div>
                  <p className={`text-sm font-semibold ${sla.color}`}>{sla.label}</p>
                </div>
              )}

              {/* Status & Priority Controls */}
              <div className="card p-3 space-y-3">
                <p className="text-[10px] font-bold text-[#8888aa] uppercase tracking-wider">Ticket Management</p>
                <div>
                  <label className="label text-[11px] mb-1">Status</label>
                  <select
                    value={ticket.status}
                    onChange={(e) => statusMutation.mutate(e.target.value)}
                    className="input-field text-xs py-1.5"
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s.replace(/_/g, " ").toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label text-[11px] mb-1">Priority</label>
                  <select
                    value={ticket.priority}
                    onChange={(e) => priorityMutation.mutate(e.target.value)}
                    className="input-field text-xs py-1.5"
                  >
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {p.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Assignment Controls */}
              <div className="card p-3 space-y-2">
                <p className="text-[10px] font-bold text-[#8888aa] uppercase tracking-wider">Assigned Agent</p>
                {ticket.assigned_agent_name ? (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-[color:var(--color-text)] flex items-center gap-1.5">
                      <User size={13} className="text-emerald-400" /> {ticket.assigned_agent_name}
                    </p>
                    <div className="flex gap-2 text-xs">
                      {ticket.assigned_to !== user?.id && (
                        <button
                          onClick={() => assignMutation.mutate()}
                          className="text-primary-400 hover:underline"
                        >
                          Assign to me
                        </button>
                      )}
                      <button
                        onClick={() => unassignMutation.mutate()}
                        className="text-red-400 hover:underline"
                      >
                        Unassign
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => assignMutation.mutate()}
                    disabled={assignMutation.isPending}
                    className="w-full btn-primary text-xs py-2"
                  >
                    Claim Ticket (Assign to me)
                  </button>
                )}
              </div>

              {/* Customer Context Card */}
              <div className="card p-3 space-y-2">
                <p className="text-[10px] font-bold text-[#8888aa] uppercase tracking-wider">Customer Profile</p>
                <div className="space-y-1 text-xs">
                  <p className="font-semibold text-[color:var(--color-text)] flex items-center gap-1.5">
                    <User size={13} className="text-primary-400" /> {ticket.customer_name || "Customer"}
                  </p>
                  {ticket.customer_email && (
                    <p className="text-[#8888aa] text-[11px] flex items-center gap-1">
                      <Mail size={11} /> {ticket.customer_email}
                    </p>
                  )}
                  {ticket.customer_user_id && (
                    <Link
                      to={`/admin/users/${ticket.customer_user_id}`}
                      className="inline-flex items-center gap-1 text-[11px] text-primary-400 hover:underline mt-1"
                    >
                      View Customer Profile <ExternalLink size={10} />
                    </Link>
                  )}
                </div>
              </div>

              {/* Order Context Card */}
              {ticket.order_id && (
                <div className="card p-3 space-y-2 bg-sky-500/5 border-sky-500/20">
                  <p className="text-[10px] font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1">
                    <Package size={12} /> Order Context
                  </p>
                  <div className="space-y-1 text-xs">
                    <p className="font-semibold font-mono text-[color:var(--color-text)]">{ticket.order_number}</p>
                    {ticket.order_status && (
                      <p className="text-[#8888aa] text-[11px] capitalize">Status: {ticket.order_status}</p>
                    )}
                    {ticket.order_total_amount && (
                      <p className="text-emerald-400 text-[11px] font-semibold">
                        Total: PKR {ticket.order_total_amount.toLocaleString()}
                      </p>
                    )}
                    <Link
                      to={`/admin/orders/${ticket.order_id}`}
                      className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:underline mt-1 font-medium"
                    >
                      View Order Details <ExternalLink size={10} />
                    </Link>
                  </div>
                </div>
              )}

              {/* AI Escalation Summary */}
              {ticket.ai_summary && (
                <div className="card p-3 space-y-2 border-primary-500/20">
                  <p className="text-[10px] font-bold text-primary-400 uppercase tracking-wider flex items-center gap-1">
                    <Bot size={12} /> AI Intelligence Summary
                  </p>
                  {ticket.ai_summary.issue_summary && (
                    <p className="text-xs text-[#8888aa] leading-relaxed">{ticket.ai_summary.issue_summary}</p>
                  )}
                  {ticket.confidence != null && (
                    <p className="text-[10px] text-[#8888aa]">Confidence: {Math.round(ticket.confidence * 100)}%</p>
                  )}
                </div>
              )}

              {/* Timeline Toggle */}
              <div className="card p-3 space-y-2">
                <button
                  onClick={() => setShowTimeline(!showTimeline)}
                  className="w-full flex items-center justify-between text-xs font-semibold text-[color:var(--color-text)]"
                >
                  Timeline Events ({ticket.timeline.length})
                  <ChevronDown size={14} className={`transition-transform ${showTimeline ? "rotate-180" : ""}`} />
                </button>
                {showTimeline && (
                  <div className="space-y-2 pt-2 border-t border-white/5">
                    {ticket.timeline.map((ev) => (
                      <div key={ev.id} className="text-[11px] space-y-0.5">
                        <p className="text-[color:var(--color-text)] font-medium">{ev.message}</p>
                        <p className="text-[#8888aa] text-[10px]">{new Date(ev.created_at).toLocaleString()}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// Mini ticket list for column 1
function OpenTicketList({ currentId, search }: { currentId?: string; search: string }) {
  const { data } = useQuery({
    queryKey: ["open-tickets-mini"],
    queryFn: () => ticketsService.listOpen({ per_page: 30 }),
    refetchInterval: 20_000,
  });

  const filtered = data?.items.filter(
    (t) =>
      !search ||
      t.ticket_number.toLowerCase().includes(search.toLowerCase()) ||
      t.subject.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="divide-y divide-white/5 flex-1 overflow-y-auto">
      {filtered?.map((t) => (
        <Link
          key={t.id}
          to={`/support/tickets/${t.id}`}
          className={`block px-3 py-3 hover:bg-white/5 transition-colors ${
            t.id === currentId ? "bg-primary-500/10 border-l-2 border-primary-500" : ""
          }`}
        >
          <div className="flex items-center justify-between gap-1 mb-1">
            <span className="text-[10px] font-mono text-primary-400 font-semibold">{t.ticket_number}</span>
            <PriorityBadge priority={t.priority} />
          </div>
          <p className="text-xs font-medium text-[color:var(--color-text)] truncate">{t.subject}</p>
          <div className="flex items-center justify-between gap-1 mt-1 text-[10px] text-[#8888aa]">
            <span className="capitalize">{t.status.replace(/_/g, " ")}</span>
            <span>{new Date(t.created_at).toLocaleDateString()}</span>
          </div>
        </Link>
      ))}
    </div>
  );
}
