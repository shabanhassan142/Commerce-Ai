// src/pages/CustomerTicketDetail.tsx
// Customer-facing support ticket conversation view

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, Bot, ExternalLink, Package, Send, User } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { PriorityBadge, StatusBadge } from "../components/ui/Badge";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import ticketsService from "../services/tickets.service";

export default function CustomerTicketDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [reply, setReply] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: ticket, isLoading, isError, refetch } = useQuery({
    queryKey: ["my-ticket", id],
    queryFn: () => ticketsService.getMine(id!),
    enabled: !!id,
    refetchInterval: 15_000,
  });

  const replyMutation = useMutation({
    mutationFn: (content: string) => ticketsService.replyMine(id!, { content }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-ticket", id] });
      setReply("");
      toast.success("Reply sent successfully");
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    },
    onError: () => toast.error("Failed to send reply. Please try again."),
  });

  if (isError) return <ErrorState message="Ticket not found." onRetry={() => refetch()} type="notfound" />;

  // Sort replies chronologically
  const thread = ticket
    ? [...ticket.replies].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    : [];

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm text-[#8888aa] hover:text-[color:var(--color-text)] transition-colors"
      >
        <ArrowLeft size={15} /> Back to My Tickets
      </button>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-10 w-1/2" />
          <Skeleton className="h-48" />
          <Skeleton className="h-24" />
        </div>
      ) : ticket ? (
        <div className="space-y-5">
          {/* Header Card */}
          <div className="card p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div>
                <span className="text-xs font-mono font-semibold text-primary-400">{ticket.ticket_number}</span>
                <h1 className="text-xl font-bold text-[color:var(--color-text)] mt-1">{ticket.subject}</h1>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <PriorityBadge priority={ticket.priority} />
                <StatusBadge status={ticket.status} />
              </div>
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs pt-3 border-t border-white/5">
              <div>
                <p className="text-[10px] text-[#8888aa] uppercase tracking-wide mb-0.5">Submitted On</p>
                <p className="text-[color:var(--color-text)] font-medium">
                  {new Date(ticket.created_at).toLocaleDateString()} at {new Date(ticket.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
              {ticket.assigned_agent_name && (
                <div>
                  <p className="text-[10px] text-[#8888aa] uppercase tracking-wide mb-0.5">Assigned Agent</p>
                  <p className="text-[color:var(--color-text)] font-medium">{ticket.assigned_agent_name}</p>
                </div>
              )}
              {ticket.sla_deadline && (
                <div>
                  <p className="text-[10px] text-[#8888aa] uppercase tracking-wide mb-0.5">SLA Target</p>
                  <p className={new Date(ticket.sla_deadline) < new Date() ? "text-red-400 font-medium" : "text-[color:var(--color-text)] font-medium"}>
                    {new Date(ticket.sla_deadline).toLocaleString()}
                  </p>
                </div>
              )}
              <div>
                <p className="text-[10px] text-[#8888aa] uppercase tracking-wide mb-0.5">Last Updated</p>
                <p className="text-[color:var(--color-text)] font-medium">
                  {new Date(ticket.updated_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Optional Associated Order Context Card */}
            {ticket.order_id && (
              <div className="card p-4 bg-white/3 border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl mt-2">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                    <Package size={18} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[color:var(--color-text)] flex items-center gap-2">
                      Associated Order: <span className="font-mono text-primary-300">{ticket.order_number}</span>
                    </p>
                    <p className="text-[11px] text-[#8888aa] mt-0.5">
                      {ticket.order_status && <span className="capitalize">Status: {ticket.order_status}</span>}
                      {ticket.order_total_amount && <span> · Total: PKR {ticket.order_total_amount.toLocaleString()}</span>}
                    </p>
                  </div>
                </div>
                <Link
                  to={`/orders/${ticket.order_id}`}
                  className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 w-fit"
                >
                  View Order <ExternalLink size={12} />
                </Link>
              </div>
            )}
          </div>

          {/* Conversation Thread */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[color:var(--color-text)]">Conversation Thread</h2>
              <span className="text-xs text-[#8888aa]">{thread.length + 1} message{thread.length !== 0 ? "s" : ""}</span>
            </div>

            <div className="p-5 space-y-5 max-h-[55vh] overflow-y-auto">
              {/* Original Message */}
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-primary-500/20 border border-primary-500/30 flex items-center justify-center flex-shrink-0">
                  <User size={14} className="text-primary-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs font-semibold text-[color:var(--color-text)]">You</span>
                    <span className="text-[10px] text-[#8888aa]">
                      {new Date(ticket.created_at).toLocaleDateString()} at {new Date(ticket.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <div className="card p-4 rounded-tl-sm bg-white/5 border-white/10">
                    <p className="text-sm text-[color:var(--color-text)] leading-relaxed whitespace-pre-wrap">{ticket.description}</p>
                  </div>
                </div>
              </motion.div>

              {/* Thread Messages */}
              {thread.map((r) => {
                const isCustomer = r.author_type === "customer";
                return (
                  <motion.div
                    key={r.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex gap-3"
                  >
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        isCustomer
                          ? "bg-primary-500/20 border border-primary-500/30"
                          : "bg-emerald-500/20 border border-emerald-500/30"
                      }`}
                    >
                      {isCustomer ? (
                        <User size={14} className="text-primary-400" />
                      ) : r.is_ai_summary ? (
                        <Bot size={14} className="text-emerald-400" />
                      ) : (
                        <span className="text-xs font-bold text-emerald-400">
                          {(r.author_name ?? "Support").charAt(0)}
                        </span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-semibold text-[color:var(--color-text)]">
                          {isCustomer ? "You" : r.author_name ?? "Support Agent"}
                        </span>
                        {r.is_ai_summary && (
                          <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                            AI Support Bot
                          </span>
                        )}
                        <span className="text-[10px] text-[#8888aa]">
                          {new Date(r.created_at).toLocaleDateString()} at {new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <div
                        className={`card p-4 ${
                          isCustomer
                            ? "rounded-tl-sm bg-white/5 border-white/10"
                            : "rounded-tl-sm bg-emerald-500/5 border-emerald-500/20"
                        }`}
                      >
                        <p className="text-sm text-[color:var(--color-text)] leading-relaxed whitespace-pre-wrap">{r.content}</p>
                      </div>
                    </div>
                  </motion.div>
                );
              })}

              <div ref={bottomRef} />
            </div>

            {/* Customer Reply Input */}
            {!["closed", "resolved"].includes(ticket.status) ? (
              <div className="p-4 border-t border-white/5 space-y-3">
                <div className="flex gap-3 items-end">
                  <textarea
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="Type your reply to the support team..."
                    rows={3}
                    className="flex-1 input-field resize-none text-sm"
                    aria-label="Reply input"
                    disabled={replyMutation.isPending}
                  />
                  <button
                    onClick={() => reply.trim() && replyMutation.mutate(reply.trim())}
                    disabled={!reply.trim() || replyMutation.isPending}
                    className="h-10 px-5 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-40 flex items-center gap-2 font-semibold text-xs text-white transition-all flex-shrink-0"
                    aria-label="Send reply"
                  >
                    <Send size={14} />
                    {replyMutation.isPending ? "Sending..." : "Send Reply"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-4 text-center text-xs text-[#8888aa] border-t border-white/5 bg-white/2">
                This ticket is marked as <span className="font-semibold text-[color:var(--color-text)] uppercase">{ticket.status}</span>. Need more help? You can create a new ticket or contact AI support.
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
