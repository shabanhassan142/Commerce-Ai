// src/pages/OrderDetail.tsx
// Full order detail with status timeline

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Bot,
  CheckCircle,
  Circle,
  CreditCard,
  MapPin,
  Package,
  Truck,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusBadge } from "../components/ui/Badge";
import ordersService from "../services/orders.service";

const ORDER_STEPS = ["pending", "confirmed", "processing", "shipped", "delivered"] as const;

function StatusTimeline({ status }: { status: string }) {
  const currentIdx = ORDER_STEPS.indexOf(status as typeof ORDER_STEPS[number]);

  return (
    <div className="flex items-center gap-0">
      {ORDER_STEPS.map((step, i) => {
        const isDone = i <= currentIdx;
        const isCurrent = i === currentIdx;
        return (
          <div key={step} className="flex items-center flex-1">
            <div className="flex flex-col items-center flex-shrink-0">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                isDone
                  ? "bg-emerald-500/20 border-2 border-emerald-500 text-emerald-400"
                  : "bg-white/5 border-2 border-white/10 text-[#8888aa]"
              } ${isCurrent ? "ring-2 ring-emerald-500/30" : ""}`}>
                {isDone ? <CheckCircle size={14} /> : <Circle size={14} />}
              </div>
              <p className={`text-[10px] font-medium mt-1.5 capitalize whitespace-nowrap ${isDone ? "text-emerald-400" : "text-[#8888aa]"}`}>
                {step}
              </p>
            </div>
            {i < ORDER_STEPS.length - 1 && (
              <div className={`h-0.5 flex-1 mx-2 rounded transition-colors ${i < currentIdx ? "bg-emerald-500" : "bg-white/10"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: order, isLoading, isError, refetch } = useQuery({
    queryKey: ["order", id],
    queryFn: () => ordersService.getById(id!),
    enabled: !!id,
  });

  if (isError) return <ErrorState message="Order not found." onRetry={() => refetch()} type="notfound" />;

  return (
    <div className="space-y-6">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-[#8888aa] hover:text-[color:var(--color-text)] transition-colors">
        <ArrowLeft size={15} /> Back to Orders
      </button>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-10 w-1/3" />
          <Skeleton className="h-32" />
          <Skeleton className="h-48" />
        </div>
      ) : order ? (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
          {/* Header */}
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-2xl font-bold text-[color:var(--color-text)]">{order.order_number}</h1>
              <p className="text-[#8888aa] text-sm mt-0.5">
                Placed {new Date(order.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={order.status} />
              <Link
                to={`/chat`}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary-500/10 border border-primary-500/20 text-primary-400 hover:bg-primary-500/20 transition-colors"
              >
                <Bot size={12} /> Ask AI
              </Link>
            </div>
          </div>

          {/* Timeline */}
          {!["cancelled"].includes(order.status) && (
            <div className="card p-6">
              <h2 className="text-sm font-semibold text-[color:var(--color-text)] mb-5">Order Timeline</h2>
              <StatusTimeline status={order.status} />
              {order.tracking_number && (
                <div className="mt-4 flex items-center gap-2 text-sm text-[#8888aa]">
                  <Truck size={14} />
                  Tracking: <span className="text-[color:var(--color-text)] font-mono font-medium">{order.tracking_number}</span>
                </div>
              )}
              {order.estimated_delivery && (
                <p className="mt-2 text-xs text-[#8888aa]">
                  Est. delivery: {new Date(order.estimated_delivery).toLocaleDateString()}
                </p>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Items */}
            <div className="lg:col-span-2 card overflow-hidden">
              <div className="px-5 py-4 border-b border-white/5">
                <h2 className="text-sm font-semibold text-[color:var(--color-text)]">
                  Items ({order.items.length})
                </h2>
              </div>
              <div className="divide-y divide-white/5">
                {order.items.map((item) => (
                  <div key={item.id} className="flex items-center gap-4 px-5 py-3">
                    <div className="w-10 h-10 rounded-xl bg-primary-500/10 flex items-center justify-center flex-shrink-0">
                      <Package size={16} className="text-primary-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[color:var(--color-text)] truncate">{item.product_name}</p>
                      {item.product_sku && <p className="text-xs text-[#8888aa]">SKU: {item.product_sku}</p>}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-sm font-semibold text-[color:var(--color-text)]">${Number(item.subtotal).toFixed(2)}</p>
                      <p className="text-xs text-[#8888aa]">{item.quantity} × ${Number(item.unit_price).toFixed(2)}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="px-5 py-3 border-t border-white/5 flex justify-between">
                <span className="text-sm font-semibold text-[color:var(--color-text)]">Total</span>
                <span className="text-lg font-bold text-[color:var(--color-text)]">${Number(order.total_amount).toFixed(2)}</span>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
              {/* Payment */}
              {order.payment && (
                <div className="card p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <CreditCard size={14} className="text-primary-400" />
                    <h3 className="text-sm font-semibold text-[color:var(--color-text)]">Payment</h3>
                  </div>
                  <div className="space-y-1.5 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">Method</span>
                      <span className="text-[color:var(--color-text)] capitalize">{order.payment.method}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">Status</span>
                      <StatusBadge status={order.payment.status} />
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">Amount</span>
                      <span className="text-[color:var(--color-text)] font-semibold">${Number(order.payment.amount).toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Notes */}
              {order.notes && (
                <div className="card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <MapPin size={14} className="text-primary-400" />
                    <h3 className="text-sm font-semibold text-[color:var(--color-text)]">Notes</h3>
                  </div>
                  <p className="text-sm text-[#8888aa]">{order.notes}</p>
                </div>
              )}

              {/* Return */}
              {order.return_request && (
                <div className="card p-4 border-amber-500/20">
                  <h3 className="text-sm font-semibold text-amber-400 mb-2">Return Request</h3>
                  <p className="text-xs text-[#8888aa]">{order.return_request.reason}</p>
                  <StatusBadge status={order.return_request.status} />
                </div>
              )}
            </div>
          </div>
        </motion.div>
      ) : null}
    </div>
  );
}
