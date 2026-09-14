// src/pages/AdminUserDetail.tsx
// Detailed customer & user profile showing full order history and support tickets

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Calendar,
  DollarSign,
  Mail,
  MapPin,
  Phone,
  ShoppingBag,
  Ticket,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { stagger, staggerItem } from "../animations/variants";
import { ErrorState } from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/Skeleton";
import adminService from "../services/admin.service";
import type { AdminUserDetail } from "../types";

export default function AdminUserDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: user, isLoading, isError, refetch } = useQuery<AdminUserDetail>({
    queryKey: ["admin-user-detail", id],
    queryFn: () => adminService.getUserDetail(id!),
    enabled: !!id,
  });

  if (isError) return <ErrorState message="Could not load user profile details." onRetry={() => refetch()} />;
  if (isLoading) return <div className="p-6 space-y-4"><SkeletonCard /><SkeletonCard /></div>;
  if (!user) return <ErrorState message="User profile not found." />;

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Back button */}
      <motion.div variants={staggerItem}>
        <button
          onClick={() => navigate("/admin/users")}
          className="inline-flex items-center gap-2 text-xs text-[#8888aa] hover:text-[color:var(--color-text)] transition-colors mb-2"
        >
          <ArrowLeft size={14} /> Back to Users Management
        </button>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center font-bold text-white text-lg">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-2">
                {user.full_name}
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary-500/20 text-primary-300 border border-primary-500/30 uppercase font-semibold">
                  {user.role}
                </span>
              </h1>
              <p className="text-xs text-[#8888aa] flex items-center gap-3 mt-1">
                <span className="flex items-center gap-1"><Mail size={12} /> {user.email}</span>
                {user.phone && <span className="flex items-center gap-1"><Phone size={12} /> {user.phone}</span>}
                <span className="flex items-center gap-1"><Calendar size={12} /> Registered {new Date(user.created_at).toLocaleDateString()}</span>
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <motion.div variants={staggerItem} className="card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
            <DollarSign size={20} />
          </div>
          <div>
            <p className="text-xs text-[#8888aa]">Total Lifetime Spent</p>
            <p className="text-xl font-bold text-emerald-400">PKR {Number(user.total_spent).toLocaleString()}</p>
          </div>
        </motion.div>

        <motion.div variants={staggerItem} className="card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-primary-500/10 text-primary-400 border border-primary-500/20 flex items-center justify-center">
            <ShoppingBag size={20} />
          </div>
          <div>
            <p className="text-xs text-[#8888aa]">Total Orders</p>
            <p className="text-xl font-bold text-[color:var(--color-text)]">{user.total_orders}</p>
          </div>
        </motion.div>

        <motion.div variants={staggerItem} className="card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center">
            <Ticket size={20} />
          </div>
          <div>
            <p className="text-xs text-[#8888aa]">Support Tickets</p>
            <p className="text-xl font-bold text-[color:var(--color-text)]">
              {user.total_tickets} ({user.open_tickets} open)
            </p>
          </div>
        </motion.div>
      </div>

      {/* Customer Orders & Support History */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Order History */}
        <motion.div variants={staggerItem} className="card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
            <ShoppingBag size={16} className="text-primary-400" /> Customer Order History
          </h2>
          {user.orders.length === 0 ? (
            <p className="text-xs text-[#8888aa] py-6 text-center">No order records found for this customer.</p>
          ) : (
            <div className="divide-y divide-white/5 text-xs">
              {user.orders.map((o) => (
                <div
                  key={o.id}
                  onClick={() => navigate(`/admin/orders/${o.id}`)}
                  className="py-3 flex items-center justify-between hover:bg-white/5 px-2 rounded-lg cursor-pointer transition-colors"
                >
                  <div>
                    <p className="font-semibold text-primary-300">{o.order_number}</p>
                    <p className="text-[#8888aa] text-[11px]">{new Date(o.created_at).toLocaleDateString()} · {o.item_count} items</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-[color:var(--color-text)]">PKR {Number(o.total_amount).toLocaleString()}</p>
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-white/10 text-white">
                      {o.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Support Tickets */}
        <motion.div variants={staggerItem} className="card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
            <Ticket size={16} className="text-amber-400" /> Customer Support Tickets
          </h2>
          {user.tickets.length === 0 ? (
            <p className="text-xs text-[#8888aa] py-6 text-center">No support tickets created by this customer.</p>
          ) : (
            <div className="divide-y divide-white/5 text-xs">
              {user.tickets.map((t) => (
                <div
                  key={t.id}
                  onClick={() => navigate(`/support/tickets/${t.id}`)}
                  className="py-3 flex items-center justify-between hover:bg-white/5 px-2 rounded-lg cursor-pointer transition-colors"
                >
                  <div>
                    <p className="font-semibold text-[color:var(--color-text)]">{t.ticket_number}</p>
                    <p className="text-[#8888aa] text-[11px] truncate max-w-[200px]">{t.subject}</p>
                  </div>
                  <div className="text-right space-y-1">
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-amber-500/15 text-amber-400">
                      {t.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Customer Addresses */}
      {user.shipping_addresses.length > 0 && (
        <motion.div variants={staggerItem} className="card p-5">
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2 mb-3">
            <MapPin size={16} className="text-emerald-400" /> Customer Saved Shipping Addresses
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {user.shipping_addresses.map((addr) => (
              <div key={addr.id} className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1">
                <p className="font-semibold text-[color:var(--color-text)]">{addr.street}</p>
                <p className="text-[#8888aa]">{addr.city}, {addr.state} {addr.postal_code}</p>
                <p className="text-[#8888aa] font-medium">{addr.country}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
