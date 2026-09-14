// src/pages/AdminOrders.tsx
// Real Customer Orders stream backed by PostgreSQL

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Search, ShoppingBag } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { stagger, staggerItem } from "../animations/variants";
import { ErrorState } from "../components/ui/ErrorState";
import { SkeletonRow } from "../components/ui/Skeleton";
import adminService from "../services/admin.service";
import type { PaginatedAdminOrders } from "../types";

export default function AdminOrders() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading, isError, refetch } = useQuery<PaginatedAdminOrders>({
    queryKey: ["admin-orders", page, search, statusFilter],
    queryFn: () =>
      adminService.getOrders({
        page,
        per_page: 15,
        search: search || undefined,
        status: statusFilter || undefined,
      }),
  });

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Header */}
      <motion.div variants={staggerItem} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-2">
            <ShoppingBag className="text-primary-400" size={24} /> Customer Orders Stream
          </h1>
          <p className="text-[#8888aa] text-sm mt-0.5">
            Real customer orders created through marketplace checkout
          </p>
        </div>
      </motion.div>

      {/* Search & Filters */}
      <motion.div variants={staggerItem} className="card p-4 flex flex-col md:flex-row gap-3">
        <div className="flex-1 relative">
          <Search size={16} className="absolute left-3 top-3 text-[#8888aa]" />
          <input
            type="text"
            placeholder="Search by order number, customer name or email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-sm text-[color:var(--color-text)] placeholder-[#8888aa] focus:outline-none focus:border-primary-500/50"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-[color:var(--color-text)] focus:outline-none"
        >
          <option value="">All Order Statuses</option>
          <option value="pending">Pending</option>
          <option value="confirmed">Confirmed</option>
          <option value="processing">Processing</option>
          <option value="shipped">Shipped</option>
          <option value="delivered">Delivered</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </motion.div>

      {/* Orders Table */}
      {isError ? (
        <ErrorState message="Could not load customer orders stream." onRetry={() => refetch()} />
      ) : (
        <motion.div variants={staggerItem} className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-[#8888aa] uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Order Number</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Placed Date</th>
                  <th className="py-3 px-4 text-center">Items</th>
                  <th className="py-3 px-4 text-center">Payment</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Total Amount</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {isLoading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i}>
                      <td colSpan={8} className="py-3 px-4">
                        <SkeletonRow />
                      </td>
                    </tr>
                  ))
                ) : data?.items.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-[#8888aa]">
                      No orders match the specified criteria.
                    </td>
                  </tr>
                ) : (
                  data?.items.map((o) => (
                    <tr
                      key={o.id}
                      onClick={() => navigate(`/admin/orders/${o.id}`)}
                      className="hover:bg-white/5 transition-colors cursor-pointer"
                    >
                      <td className="py-3 px-4 font-semibold text-primary-300">
                        {o.order_number}
                      </td>
                      <td className="py-3 px-4">
                        <p className="font-semibold text-[color:var(--color-text)]">{o.customer_name}</p>
                        <p className="text-[11px] text-[#8888aa]">{o.customer_email}</p>
                      </td>
                      <td className="py-3 px-4 text-[#8888aa]">
                        {new Date(o.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-center font-medium text-[color:var(--color-text)]">
                        {o.item_count} items
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-white/5 border border-white/10">
                          {o.payment_method ?? "card"} ({o.payment_status ?? "completed"})
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            o.status === "delivered"
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                              : o.status === "cancelled"
                              ? "bg-red-500/20 text-red-400 border border-red-500/30"
                              : "bg-primary-500/20 text-primary-300 border border-primary-500/30"
                          }`}
                        >
                          {o.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-emerald-400">
                        PKR {Number(o.total_amount).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button className="text-primary-400 hover:text-primary-300 p-1">
                          <ArrowRight size={14} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {data && data.pages > 1 && (
            <div className="px-4 py-3 border-t border-white/10 flex items-center justify-between text-xs text-[#8888aa]">
              <span>
                Page {data.page} of {data.pages} ({data.total} total orders)
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  className="px-3 py-1 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={page >= data.pages}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}
