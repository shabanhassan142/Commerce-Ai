// src/pages/AdminAnalytics.tsx
// Data-Driven Real Analytics page connected to PostgreSQL

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  BarChart3,
  Bot,
  DollarSign,
  ShoppingBag,
  TrendingUp,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { stagger, staggerItem } from "../animations/variants";
import { ErrorState } from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/Skeleton";
import adminService from "../services/admin.service";
import type { AdminAnalyticsData } from "../types";

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#d946ef", "#06b6d4", "#8b5cf6"];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="card px-3 py-2 text-xs space-y-1 shadow-xl border border-white/10 bg-[#16162a]">
      {label && <p className="text-white font-semibold">{label}</p>}
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color || "#6366f1" }}>
          {p.name}: {typeof p.value === "number" && p.name.toLowerCase().includes("revenue") ? `PKR ${p.value.toLocaleString()}` : p.value}
        </p>
      ))}
    </div>
  );
};

export default function AdminAnalytics() {
  const { data, isLoading, isError, refetch } = useQuery<AdminAnalyticsData>({
    queryKey: ["admin-analytics-real"],
    queryFn: () => adminService.getAnalytics(),
    refetchInterval: 60_000,
  });

  if (isError) return <ErrorState message="Could not load real-time database analytics." onRetry={() => refetch()} />;

  const formatPKR = (val?: number) => {
    if (val == null) return "PKR 0";
    return `PKR ${Number(val).toLocaleString()}`;
  };

  const stockChartData = data
    ? [
        { name: "In Stock", value: data.stock_status_summary.in_stock },
        { name: "Low Stock", value: data.stock_status_summary.low_stock },
        { name: "Out of Stock", value: data.stock_status_summary.out_of_stock },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Header */}
      <motion.div variants={staggerItem} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-2">
            <BarChart3 className="text-primary-400" size={24} /> Platform Real-Time Analytics
          </h1>
          <p className="text-[#8888aa] text-sm mt-0.5">
            Aggregated financial, customer, catalog, and support performance metrics calculated directly from PostgreSQL
          </p>
        </div>
      </motion.div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <motion.div variants={staggerItem} className="card p-5">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center mb-3">
                <DollarSign size={18} />
              </div>
              <p className="text-2xl font-bold text-emerald-400">{formatPKR(data?.total_revenue)}</p>
              <p className="text-xs text-[#8888aa] mt-1">Total Lifetime Revenue</p>
              <p className="text-[11px] text-[#8888aa] mt-1">Avg Order: {formatPKR(data?.average_order_value)}</p>
            </motion.div>

            <motion.div variants={staggerItem} className="card p-5">
              <div className="w-9 h-9 rounded-xl bg-primary-500/10 text-primary-400 border border-primary-500/20 flex items-center justify-center mb-3">
                <ShoppingBag size={18} />
              </div>
              <p className="text-2xl font-bold text-[color:var(--color-text)]">{data?.total_orders ?? 0}</p>
              <p className="text-xs text-[#8888aa] mt-1">Total Completed Orders</p>
            </motion.div>

            <motion.div variants={staggerItem} className="card p-5">
              <div className="w-9 h-9 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center justify-center mb-3">
                <Users size={18} />
              </div>
              <p className="text-2xl font-bold text-[color:var(--color-text)]">{data?.total_customers ?? 0}</p>
              <p className="text-xs text-[#8888aa] mt-1">Total Customers</p>
              <p className="text-[11px] text-purple-400 mt-1">Repeat Rate: {data?.repeat_customer_rate ?? 0}%</p>
            </motion.div>

            <motion.div variants={staggerItem} className="card p-5">
              <div className="w-9 h-9 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center mb-3">
                <Bot size={18} />
              </div>
              <p className="text-2xl font-bold text-amber-400">{data?.ai_resolution_rate ?? 0}%</p>
              <p className="text-xs text-[#8888aa] mt-1">AI Resolution Rate</p>
              <p className="text-[11px] text-[#8888aa] mt-1">Overall SLA: {data?.resolution_rate ?? 0}%</p>
            </motion.div>
          </>
        )}
      </div>

      {/* Sales & Orders Trends */}
      {!isLoading && data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Revenue Trend */}
          <motion.div variants={staggerItem} className="card p-5">
            <h2 className="text-sm font-semibold text-[color:var(--color-text)] mb-4">Revenue Trend (Last 7 Days)</h2>
            {data.revenue_trend.some((d) => d.revenue > 0) ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={data.revenue_trend} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRevAnalytics" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8888aa" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#8888aa" }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="revenue" name="Revenue (PKR)" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorRevAnalytics)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-xs text-[#8888aa]">No revenue data recorded yet.</div>
            )}
          </motion.div>

          {/* Orders Volume Trend */}
          <motion.div variants={staggerItem} className="card p-5">
            <h2 className="text-sm font-semibold text-[color:var(--color-text)] mb-4">Order Volume Trend (Last 7 Days)</h2>
            {data.orders_trend.some((d) => d.orders > 0) ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.orders_trend} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8888aa" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#8888aa" }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="orders" name="Completed Orders" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-xs text-[#8888aa]">No order volume recorded yet.</div>
            )}
          </motion.div>
        </div>
      )}

      {/* Catalog & Performance Breakdown */}
      {!isLoading && data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Best Selling Products */}
          <motion.div variants={staggerItem} className="lg:col-span-2 card p-5 space-y-4">
            <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
              <TrendingUp size={16} className="text-emerald-400" /> Best-Selling Catalog Products
            </h2>
            {data.best_selling_products.length === 0 ? (
              <p className="text-xs text-[#8888aa] py-6 text-center">No catalog sales recorded yet.</p>
            ) : (
              <div className="divide-y divide-white/5 text-xs">
                {data.best_selling_products.map((p, i) => (
                  <div key={i} className="py-2.5 flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-[color:var(--color-text)]">{p.name}</p>
                      <p className="text-[#8888aa] text-[11px]">{p.units_sold} units sold</p>
                    </div>
                    <p className="font-bold text-emerald-400">PKR {Number(p.revenue).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            )}
          </motion.div>

          {/* Catalog Stock Status Distribution */}
          <motion.div variants={staggerItem} className="card p-5 flex flex-col">
            <h2 className="text-sm font-semibold text-[color:var(--color-text)] mb-4">Stock Status Overview</h2>
            {stockChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={stockChartData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value">
                    {stockChartData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend iconSize={9} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex-1 flex items-center justify-center text-xs text-[#8888aa]">No stock status data</div>
            )}
          </motion.div>
        </div>
      )}
    </motion.div>
  );
}
