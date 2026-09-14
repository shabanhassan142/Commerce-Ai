// src/pages/AdminOrderDetail.tsx
// Comprehensive Admin Order Detail view displaying customer info, line items, payment status, shipping address, and order timeline

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Calendar,
  CreditCard,
  Mail,
  MapPin,
  Package,
  Ticket,
  User,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { stagger, staggerItem } from "../animations/variants";
import { ErrorState } from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/Skeleton";
import adminService from "../services/admin.service";
import type { AdminOrderDetail } from "../types";

export default function AdminOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: order, isLoading, isError, refetch } = useQuery<AdminOrderDetail>({
    queryKey: ["admin-order-detail", id],
    queryFn: () => adminService.getOrderDetail(id!),
    enabled: !!id,
  });

  const updateStatusMutation = useMutation({
    mutationFn: (newStatus: string) => adminService.updateOrderStatus(id!, newStatus),
    onSuccess: (_, newStatus) => {
      toast.success(`Order status updated to ${newStatus}`);
      queryClient.invalidateQueries({ queryKey: ["admin-order-detail", id] });
      queryClient.invalidateQueries({ queryKey: ["admin-orders"] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.message || "Failed to update order status");
    },
  });

  if (isError) return <ErrorState message="Could not load order details." onRetry={() => refetch()} />;
  if (isLoading) return <div className="p-6 space-y-4"><SkeletonCard /><SkeletonCard /></div>;
  if (!order) return <ErrorState message="Order not found." />;

  const customerName = order.customer.full_name || "Customer";
  const customerEmail = order.customer.email || "N/A";
  const customerUserId = order.customer.user_id;

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Back button */}
      <motion.div variants={staggerItem}>
        <button
          onClick={() => navigate("/admin/orders")}
          className="inline-flex items-center gap-2 text-xs text-[#8888aa] hover:text-[color:var(--color-text)] transition-colors mb-2"
        >
          <ArrowLeft size={14} /> Back to Customer Orders Stream
        </button>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-3">
              Order {order.order_number}
              <span className="text-xs px-3 py-1 rounded-full font-bold uppercase bg-primary-500/20 text-primary-300 border border-primary-500/30">
                {order.status}
              </span>
            </h1>
            <p className="text-xs text-[#8888aa] flex items-center gap-3 mt-1">
              <span className="flex items-center gap-1"><Calendar size={12} /> Placed on {new Date(order.created_at).toLocaleString()}</span>
              {order.tracking_number && <span>Tracking: <strong className="font-mono text-white">{order.tracking_number}</strong></span>}
            </p>
          </div>

          {/* Admin Status Controls */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#8888aa]">Update Status:</span>
            <select
              value={order.status}
              disabled={updateStatusMutation.isPending}
              onChange={(e) => updateStatusMutation.mutate(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-[color:var(--color-text)] font-semibold focus:outline-none cursor-pointer"
            >
              <option value="pending">Pending</option>
              <option value="confirmed">Confirmed</option>
              <option value="processing">Processing</option>
              <option value="shipped">Shipped</option>
              <option value="delivered">Delivered</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </motion.div>

      {/* Customer & Shipping Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Customer Profile Card */}
        <motion.div variants={staggerItem} className="card p-5 space-y-3">
          <h2 className="text-xs font-semibold text-[#8888aa] uppercase tracking-wider flex items-center gap-1.5">
            <User size={14} className="text-primary-400" /> Customer Information
          </h2>
          <div>
            <p
              onClick={() => customerUserId && navigate(`/admin/users/${customerUserId}`)}
              className="text-sm font-bold text-[color:var(--color-text)] hover:text-primary-300 cursor-pointer transition-colors"
            >
              {customerName}
            </p>
            <p className="text-xs text-[#8888aa] flex items-center gap-1 mt-0.5"><Mail size={11} /> {customerEmail}</p>
          </div>
          {customerUserId && (
            <button
              onClick={() => navigate(`/admin/users/${customerUserId}`)}
              className="text-xs text-primary-400 hover:underline inline-block"
            >
              View Full Customer Profile →
            </button>
          )}
        </motion.div>

        {/* Shipping Address Card */}
        <motion.div variants={staggerItem} className="card p-5 space-y-3">
          <h2 className="text-xs font-semibold text-[#8888aa] uppercase tracking-wider flex items-center gap-1.5">
            <MapPin size={14} className="text-emerald-400" /> Shipping Destination
          </h2>
          {order.shipping_address ? (
            <div className="text-xs space-y-0.5 text-[color:var(--color-text)]">
              <p className="font-semibold">{order.shipping_address.street}</p>
              <p className="text-[#8888aa]">{order.shipping_address.city}, {order.shipping_address.state} {order.shipping_address.postal_code}</p>
              <p className="text-[#8888aa] font-medium">{order.shipping_address.country}</p>
            </div>
          ) : (
            <p className="text-xs text-[#8888aa]">No address recorded.</p>
          )}
        </motion.div>

        {/* Payment Summary Card */}
        <motion.div variants={staggerItem} className="card p-5 space-y-3">
          <h2 className="text-xs font-semibold text-[#8888aa] uppercase tracking-wider flex items-center gap-1.5">
            <CreditCard size={14} className="text-purple-400" /> Payment Details
          </h2>
          {order.payment ? (
            <div className="text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-[#8888aa]">Payment Method:</span>
                <span className="font-semibold uppercase text-white">{order.payment.method}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#8888aa]">Payment Status:</span>
                <span className="font-semibold uppercase text-emerald-400">{order.payment.status}</span>
              </div>
              {order.payment.transaction_id && (
                <div className="flex justify-between">
                  <span className="text-[#8888aa]">Transaction:</span>
                  <span className="font-mono text-[11px] text-white">{order.payment.transaction_id}</span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-[#8888aa]">Demo Checkout Payment Recorded.</p>
          )}
        </motion.div>
      </div>

      {/* Order Line Items */}
      <motion.div variants={staggerItem} className="card overflow-hidden p-5 space-y-4">
        <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
          <Package size={16} className="text-primary-400" /> Order Items ({order.items.length})
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/10 bg-white/5 text-[#8888aa] uppercase font-semibold">
                <th className="py-2.5 px-3">Product</th>
                <th className="py-2.5 px-3 text-center">Unit Price</th>
                <th className="py-2.5 px-3 text-center">Quantity</th>
                <th className="py-2.5 px-3 text-right">Line Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {order.items.map((item) => (
                <tr key={item.id} className="hover:bg-white/5">
                  <td className="py-3 px-3">
                    <div
                      onClick={() => navigate(`/admin/products/${item.product_id}`)}
                      className="flex items-center gap-3 cursor-pointer group"
                    >
                      <div>
                        <p className="font-semibold text-[color:var(--color-text)] group-hover:text-primary-300 transition-colors">
                          {item.product_name}
                        </p>
                        {item.product_sku && <p className="text-[10px] text-[#8888aa] font-mono">SKU: {item.product_sku}</p>}
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center text-[#8888aa]">
                    PKR {Number(item.unit_price).toLocaleString()}
                  </td>
                  <td className="py-3 px-3 text-center font-bold text-[color:var(--color-text)]">
                    {item.quantity}
                  </td>
                  <td className="py-3 px-3 text-right font-bold text-emerald-400">
                    PKR {Number(item.subtotal).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Total Summary */}
        <div className="border-t border-white/10 pt-3 flex justify-end">
          <div className="w-64 space-y-1.5 text-xs">
            <div className="flex justify-between text-[#8888aa]">
              <span>Subtotal:</span>
              <span>PKR {Number(order.total_amount).toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[#8888aa]">
              <span>Shipping:</span>
              <span>Free</span>
            </div>
            <div className="flex justify-between text-sm font-bold text-white border-t border-white/10 pt-1.5">
              <span>Total Paid:</span>
              <span className="text-emerald-400">PKR {Number(order.total_amount).toLocaleString()}</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Linked Support Tickets */}
      {order.tickets && order.tickets.length > 0 && (
        <motion.div variants={staggerItem} className="card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
            <Ticket size={16} className="text-amber-400" /> Support Tickets Linked to this Order
          </h2>
          <div className="divide-y divide-white/5 text-xs">
            {order.tickets.map((t) => (
              <div
                key={t.id}
                onClick={() => navigate(`/support/tickets/${t.id}`)}
                className="py-2.5 flex items-center justify-between hover:bg-white/5 px-2 rounded-lg cursor-pointer transition-colors"
              >
                <div>
                  <p className="font-semibold text-primary-300">{t.ticket_number}</p>
                  <p className="text-[#8888aa] text-[11px]">{t.subject}</p>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-amber-500/20 text-amber-400">
                  {t.status}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
