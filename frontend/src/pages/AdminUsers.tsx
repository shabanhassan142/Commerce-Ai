// src/pages/AdminUsers.tsx
// Real User & Customer management page backed by PostgreSQL

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Search, Shield, Users } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { stagger, staggerItem } from "../animations/variants";
import { ErrorState } from "../components/ui/ErrorState";
import { SkeletonRow } from "../components/ui/Skeleton";
import adminService from "../services/admin.service";
import type { PaginatedAdminUsers } from "../types";

export default function AdminUsers() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading, isError, refetch } = useQuery<PaginatedAdminUsers>({
    queryKey: ["admin-users", page, search, roleFilter, statusFilter],
    queryFn: () =>
      adminService.getUsers({
        page,
        per_page: 15,
        search: search || undefined,
        role: roleFilter || undefined,
        status: statusFilter || undefined,
      }),
  });

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Header */}
      <motion.div variants={staggerItem} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-2">
            <Users className="text-primary-400" size={24} /> User & Customer Management
          </h1>
          <p className="text-[#8888aa] text-sm mt-0.5">
            Real customer accounts, support staff, and admin accounts registered in database
          </p>
        </div>
      </motion.div>

      {/* Search & Filters */}
      <motion.div variants={staggerItem} className="card p-4 flex flex-col md:flex-row gap-3">
        <div className="flex-1 relative">
          <Search size={16} className="absolute left-3 top-3 text-[#8888aa]" />
          <input
            type="text"
            placeholder="Search by full name or email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-sm text-[color:var(--color-text)] placeholder-[#8888aa] focus:outline-none focus:border-primary-500/50"
          />
        </div>
        <div className="flex gap-2">
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-[color:var(--color-text)] focus:outline-none"
          >
            <option value="">All Roles</option>
            <option value="customer">Customer</option>
            <option value="support">Support</option>
            <option value="admin">Admin</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-[color:var(--color-text)] focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </motion.div>

      {/* Users Table */}
      {isError ? (
        <ErrorState message="Could not load user records." onRetry={() => refetch()} />
      ) : (
        <motion.div variants={staggerItem} className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-[#8888aa] uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Registered</th>
                  <th className="py-3 px-4 text-center">Orders</th>
                  <th className="py-3 px-4 text-right">Total Spent</th>
                  <th className="py-3 px-4 text-center">Tickets</th>
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
                      No users match the search filters.
                    </td>
                  </tr>
                ) : (
                  data?.items.map((u) => (
                    <tr
                      key={u.id}
                      onClick={() => navigate(`/admin/users/${u.id}`)}
                      className="hover:bg-white/5 transition-colors cursor-pointer"
                    >
                      <td className="py-3 px-4">
                        <p className="font-semibold text-[color:var(--color-text)]">{u.full_name}</p>
                        <p className="text-[11px] text-[#8888aa]">{u.email}</p>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            u.role === "admin"
                              ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                              : u.role === "support"
                              ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                              : "bg-primary-500/20 text-primary-300 border border-primary-500/30"
                          }`}
                        >
                          {u.role === "admin" && <Shield size={10} />}
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 text-[11px] font-medium ${
                            u.is_active ? "text-emerald-400" : "text-red-400"
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? "bg-emerald-400" : "bg-red-400"}`} />
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-[#8888aa]">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-center font-medium text-[color:var(--color-text)]">
                        {u.total_orders}
                      </td>
                      <td className="py-3 px-4 text-right font-semibold text-emerald-400">
                        PKR {Number(u.total_spent).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-amber-400 font-medium">
                          {u.total_tickets} ({u.open_tickets} open)
                        </span>
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
                Page {data.page} of {data.pages} ({data.total} total users)
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
