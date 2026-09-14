// src/pages/Orders.tsx
// Customer orders list

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ShoppingBag } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Pagination } from "../components/ui/Pagination";
import { SkeletonTable } from "../components/ui/Skeleton";
import { StatusBadge } from "../components/ui/Badge";
import ordersService from "../services/orders.service";

const STATUS_TABS = ["", "pending", "confirmed", "processing", "shipped", "delivered", "cancelled"] as const;

export default function Orders() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["orders", { page, status }],
    queryFn: () => ordersService.list({ page, per_page: 15, status: status || undefined }),
  });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[color:var(--color-text)]">My Orders</h1>
        <p className="text-[#8888aa] text-sm mt-0.5">
          {data ? `${data.total} orders` : "Track and manage your orders"}
        </p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {STATUS_TABS.map((s) => (
          <button
            key={s || "all"}
            onClick={() => { setStatus(s); setPage(1); }}
            className={`flex-shrink-0 px-4 py-1.5 rounded-full text-xs font-medium capitalize transition-colors ${
              status === s ? "bg-primary-600 text-white" : "bg-white/5 text-[#8888aa] hover:bg-white/10 hover:text-[color:var(--color-text)]"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Content */}
      {isError ? (
        <ErrorState message="Couldn't load orders." onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="card p-5"><SkeletonTable rows={6} /></div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon={ShoppingBag}
          title="No orders yet"
          description="Start shopping to see your orders here."
          action={{ label: "Browse Products", href: "/products" }}
        />
      ) : (
        <>
          {/* Desktop table */}
          <div className="card overflow-hidden hidden md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left">
                  {["Order", "Date", "Items", "Total", "Status", ""].map((h) => (
                    <th key={h} className="px-5 py-3 text-xs font-semibold text-[#8888aa] uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {data?.items.map((order) => (
                  <motion.tr
                    key={order.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-white/3 transition-colors"
                  >
                    <td className="px-5 py-3 font-medium text-[color:var(--color-text)]">{order.order_number}</td>
                    <td className="px-5 py-3 text-[#8888aa]">{new Date(order.created_at).toLocaleDateString()}</td>
                    <td className="px-5 py-3 text-[#8888aa]">{order.item_count} item{order.item_count !== 1 ? "s" : ""}</td>
                    <td className="px-5 py-3 font-semibold text-[color:var(--color-text)]">${Number(order.total_amount).toFixed(2)}</td>
                    <td className="px-5 py-3"><StatusBadge status={order.status} /></td>
                    <td className="px-5 py-3">
                      <Link to={`/orders/${order.id}`} className="text-primary-400 hover:text-primary-300 text-xs font-medium">
                        View →
                      </Link>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {data?.items.map((order) => (
              <Link key={order.id} to={`/orders/${order.id}`} className="card p-4 block card-hover">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="text-sm font-semibold text-[color:var(--color-text)]">{order.order_number}</p>
                    <p className="text-xs text-[#8888aa]">{new Date(order.created_at).toLocaleDateString()}</p>
                  </div>
                  <StatusBadge status={order.status} />
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-[#8888aa]">{order.item_count} item{order.item_count !== 1 ? "s" : ""}</p>
                  <p className="text-sm font-bold text-[color:var(--color-text)]">${Number(order.total_amount).toFixed(2)}</p>
                </div>
              </Link>
            ))}
          </div>

          {data && (
            <Pagination page={data.page} pages={data.pages} total={data.total} perPage={data.per_page} onPageChange={setPage} />
          )}
        </>
      )}
    </div>
  );
}
