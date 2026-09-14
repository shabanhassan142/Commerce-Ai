// src/pages/AdminProducts.tsx
// Real Product Catalog & Inventory Management backed by PostgreSQL

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Package, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { stagger, staggerItem } from "../animations/variants";
import { ErrorState } from "../components/ui/ErrorState";
import { SkeletonRow } from "../components/ui/Skeleton";
import adminService from "../services/admin.service";
import type { PaginatedAdminProducts } from "../types";

export default function AdminProducts() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [stockStatusFilter, setStockStatusFilter] = useState("");

  const { data, isLoading, isError, refetch } = useQuery<PaginatedAdminProducts>({
    queryKey: ["admin-products", page, search, stockStatusFilter],
    queryFn: () =>
      adminService.getProducts({
        page,
        per_page: 15,
        search: search || undefined,
        stock_status: stockStatusFilter || undefined,
      }),
  });

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Header */}
      <motion.div variants={staggerItem} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-2">
            <Package className="text-sky-400" size={24} /> Product Catalog & Inventory
          </h1>
          <p className="text-[#8888aa] text-sm mt-0.5">
            Real catalog items, live inventory stock levels, prices, and unit sales metrics
          </p>
        </div>
      </motion.div>

      {/* Search & Filters */}
      <motion.div variants={staggerItem} className="card p-4 flex flex-col md:flex-row gap-3">
        <div className="flex-1 relative">
          <Search size={16} className="absolute left-3 top-3 text-[#8888aa]" />
          <input
            type="text"
            placeholder="Search by product name or SKU..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-sm text-[color:var(--color-text)] placeholder-[#8888aa] focus:outline-none focus:border-primary-500/50"
          />
        </div>
        <select
          value={stockStatusFilter}
          onChange={(e) => {
            setStockStatusFilter(e.target.value);
            setPage(1);
          }}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-[color:var(--color-text)] focus:outline-none"
        >
          <option value="">All Stock Levels</option>
          <option value="in_stock">In Stock</option>
          <option value="low_stock">Low Stock (≤ 5)</option>
          <option value="out_of_stock">Out of Stock (0)</option>
        </select>
      </motion.div>

      {/* Products Table */}
      {isError ? (
        <ErrorState message="Could not load product inventory records." onRetry={() => refetch()} />
      ) : (
        <motion.div variants={staggerItem} className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-[#8888aa] uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Product</th>
                  <th className="py-3 px-4">SKU</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4 text-right">Price</th>
                  <th className="py-3 px-4 text-center">Stock Level</th>
                  <th className="py-3 px-4 text-center">Units Sold</th>
                  <th className="py-3 px-4 text-right">Total Revenue</th>
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
                      No catalog products match the specified criteria.
                    </td>
                  </tr>
                ) : (
                  data?.items.map((p) => (
                    <tr
                      key={p.id}
                      onClick={() => navigate(`/admin/products/${p.id}`)}
                      className="hover:bg-white/5 transition-colors cursor-pointer"
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          {p.primary_image_url ? (
                            <img src={p.primary_image_url} alt={p.name} className="w-9 h-9 rounded-lg object-cover bg-white/5" />
                          ) : (
                            <div className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center text-xs">📦</div>
                          )}
                          <div>
                            <p className="font-semibold text-[color:var(--color-text)] truncate max-w-[200px]">{p.name}</p>
                            {p.brand && <p className="text-[11px] text-[#8888aa]">{p.brand}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-[#8888aa]">{p.sku}</td>
                      <td className="py-3 px-4 text-[#8888aa]">{p.category_name ?? "—"}</td>
                      <td className="py-3 px-4 text-right font-semibold text-primary-300">
                        PKR {Number(p.price).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            p.stock === 0
                              ? "bg-red-500/20 text-red-400 border border-red-500/30"
                              : p.stock <= 5
                              ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                              : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          }`}
                        >
                          {p.stock === 0 ? "Out of Stock" : `${p.stock} in stock`}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-medium text-[color:var(--color-text)]">
                        {p.units_sold}
                      </td>
                      <td className="py-3 px-4 text-right font-semibold text-emerald-400">
                        PKR {Number(p.total_revenue).toLocaleString()}
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
                Page {data.page} of {data.pages} ({data.total} total products)
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
