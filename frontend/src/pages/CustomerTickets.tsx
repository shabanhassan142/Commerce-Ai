// src/pages/CustomerTickets.tsx
// Customer Support Center — Ticket List + Create Ticket Modal

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bot, MessageSquare, Plus, Ticket, X } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { PriorityBadge, StatusBadge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Pagination } from "../components/ui/Pagination";
import { SkeletonTable } from "../components/ui/Skeleton";
import ordersService from "../services/orders.service";
import ticketsService from "../services/tickets.service";

const CATEGORIES = [
  "Order Issue",
  "Product Question",
  "Payment",
  "Delivery",
  "Return / Refund",
  "Account",
  "Technical Issue",
  "Other",
] as const;

function CreateTicketModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();

  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState<string>("Order Issue");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high" | "urgent">("medium");
  const [orderId, setOrderId] = useState<string>("");

  // Fetch customer's own orders for the order dropdown
  const { data: customerOrders } = useQuery({
    queryKey: ["customer-orders-dropdown"],
    queryFn: () => ordersService.list({ page: 1, per_page: 50 }),
  });

  const mutation = useMutation({
    mutationFn: ticketsService.create,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["my-tickets"] });
      toast.success(`Ticket ${data.ticket_number} created successfully 🎉`);
      onClose();
      navigate(`/my/tickets/${data.id}`);
    },
    onError: () => toast.error("Failed to create ticket. Please try again."),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) return;

    // Combine category with subject for clarity
    const fullSubject = `[${category}] ${subject.trim()}`;

    mutation.mutate({
      subject: fullSubject,
      description: description.trim(),
      priority,
      order_id: orderId || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative card w-full max-w-lg p-6 space-y-4 z-10 overflow-y-auto max-h-[90vh]"
        role="dialog"
        aria-labelledby="create-ticket-title"
      >
        <div className="flex items-center justify-between border-b border-white/5 pb-3">
          <div>
            <h2 id="create-ticket-title" className="text-lg font-bold text-[color:var(--color-text)]">
              Create Support Ticket
            </h2>
            <p className="text-xs text-[#8888aa]">Submit a request to our support team</p>
          </div>
          <button onClick={onClose} className="text-[#8888aa] hover:text-[color:var(--color-text)] p-1">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-sm">
          {/* Category */}
          <div>
            <label className="label" htmlFor="ticket-category">Category</label>
            <select
              id="ticket-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="input-field"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Subject */}
          <div>
            <label className="label" htmlFor="ticket-subject">Subject</label>
            <input
              id="ticket-subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Brief summary of your issue"
              className="input-field"
              required
              minLength={3}
              maxLength={200}
            />
          </div>

          {/* Associate Order (Optional) */}
          <div>
            <label className="label" htmlFor="ticket-order">Associated Order (Optional)</label>
            <select
              id="ticket-order"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              className="input-field"
            >
              <option value="">None / Not Order Related</option>
              {customerOrders?.items.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.order_number} — PKR {Number(o.total_amount).toLocaleString()} ({new Date(o.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>

          {/* Priority */}
          <div>
            <label className="label" htmlFor="ticket-priority">Priority</label>
            <select
              id="ticket-priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as typeof priority)}
              className="input-field"
            >
              <option value="low">Low — General inquiry</option>
              <option value="medium">Normal — Standard request</option>
              <option value="high">High — Needs fast attention</option>
              <option value="urgent">Urgent — Critical order/delivery issue</option>
            </select>
          </div>

          {/* Message / Description */}
          <div>
            <label className="label" htmlFor="ticket-description">Detailed Message</label>
            <textarea
              id="ticket-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Please provide full details about your problem or question..."
              rows={4}
              className="input-field resize-none"
              required
              minLength={5}
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={mutation.isPending} className="btn-primary flex-1 py-2.5">
              {mutation.isPending ? "Submitting…" : "Submit Ticket"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-white/10 text-sm text-[#8888aa] hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

const STATUS_TABS = ["", "open", "in_progress", "waiting_for_customer", "resolved", "closed"] as const;
const TAB_LABELS: Record<string, string> = {
  "": "All Tickets",
  open: "Open",
  in_progress: "In Progress",
  waiting_for_customer: "Waiting for Customer",
  resolved: "Resolved",
  closed: "Closed",
};

export default function CustomerTickets() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["my-tickets", { page, status }],
    queryFn: () => ticketsService.listMine({ page, per_page: 15, status: status || undefined }),
  });

  return (
    <div className="space-y-6">
      {showCreate && <CreateTicketModal onClose={() => setShowCreate(false)} />}

      {/* Help Center Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 card p-6 bg-gradient-to-r from-primary-950/40 via-card to-card border-primary-500/20">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)]">How can we help you? 👋</h1>
          <p className="text-[#8888aa] text-sm mt-1">
            Submit a support ticket or get instant help from our AI Assistant.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            to="/chat"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-xs font-semibold text-[color:var(--color-text)] hover:bg-white/10 transition-colors"
          >
            <Bot size={16} className="text-primary-400" /> Ask CommerceFlow AI
          </Link>
          <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2 text-xs py-2.5">
            <Plus size={16} /> Create Support Ticket
          </button>
        </div>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {STATUS_TABS.map((s) => (
          <button
            key={s || "all"}
            onClick={() => {
              setStatus(s);
              setPage(1);
            }}
            className={`flex-shrink-0 px-4 py-1.5 rounded-full text-xs font-medium transition-colors ${
              status === s
                ? "bg-primary-600 text-white"
                : "bg-white/5 text-[#8888aa] hover:bg-white/10 hover:text-[color:var(--color-text)]"
            }`}
          >
            {TAB_LABELS[s]}
          </button>
        ))}
      </div>

      {/* Ticket List Content */}
      {isError ? (
        <ErrorState message="Could not load your support tickets." onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="card p-5"><SkeletonTable rows={5} /></div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon={Ticket}
          title="No support tickets found"
          description="You haven't submitted any support requests yet. Need help with an order or product?"
          action={{ label: "Create Ticket", onClick: () => setShowCreate(true) }}
        />
      ) : (
        <>
          <div className="space-y-3">
            {data?.items.map((ticket) => (
              <Link
                key={ticket.id}
                to={`/my/tickets/${ticket.id}`}
                className="card p-5 block card-hover transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3.5 min-w-0">
                    <div className="w-9 h-9 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <MessageSquare size={16} className="text-primary-400" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-xs font-mono font-semibold text-primary-400">{ticket.ticket_number}</span>
                        <PriorityBadge priority={ticket.priority} />
                      </div>
                      <p className="text-sm font-semibold text-[color:var(--color-text)] truncate">{ticket.subject}</p>
                      <p className="text-xs text-[#8888aa] mt-1 flex items-center gap-2">
                        <span>Created: {new Date(ticket.created_at).toLocaleDateString()}</span>
                        {ticket.updated_at && <span>· Updated: {new Date(ticket.updated_at).toLocaleDateString()}</span>}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <StatusBadge status={ticket.status} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
          {data && (
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              perPage={data.per_page}
              onPageChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}
