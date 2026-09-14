// src/pages/AdminDashboard.tsx
// Data-Driven Platform Overview Dashboard connected to PostgreSQL

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle,
  DollarSign,
  Package,
  ShoppingBag,
  Ticket,
  Users,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import {
  Area,
  AreaChart,
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
import type { AdminDashboardData } from "../types";

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#8b5cf6"];

function StatCard({
  icon: Icon,
  label,
  value,
  subText,
  color = "primary",
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subText?: string;
  color?: "primary" | "emerald" | "amber" | "red" | "sky" | "purple";
  onClick?: () => void;
}) {
  const styles: Record<string, string> = {
    primary: "bg-primary-500/10 text-primary-400 border-primary-500/20",
    emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    red: "bg-red-500/10 text-red-400 border-red-500/20",
    sky: "bg-sky-500/10 text-sky-400 border-sky-500/20",
    purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  };

  return (
    <motion.div
      variants={staggerItem}
      onClick={onClick}
      className={`card p-5 transition-all duration-200 ${
        onClick ? "cursor-pointer hover:border-primary-500/40 hover:scale-[1.01]" : ""
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${styles[color]}`}>
          <Icon size={18} />
        </div>
        {onClick && <ArrowRight size={14} className="text-[#8888aa] group-hover:text-primary-400" />}
      </div>
      <p className="text-2xl font-bold text-[color:var(--color-text)] tracking-tight">{value}</p>
      <p className="text-xs font-medium text-[#8888aa] mt-1">{label}</p>
      {subText && <p className="text-[11px] text-primary-400/80 mt-1">{subText}</p>}
    </motion.div>
  );
}

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

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useQuery<AdminDashboardData>({
    queryKey: ["admin-dashboard-real"],
    queryFn: () => adminService.getDashboardData(),
    refetchInterval: 30_000,
  });

  if (isError) return <ErrorState message="Could not load real-time admin metrics from database." onRetry={() => refetch()} />;

  const formatPKR = (val?: number) => {
    if (val == null) return "PKR 0";
    return `PKR ${Number(val).toLocaleString()}`;
  };

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Header */}
      <motion.div variants={staggerItem} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-2">
            Admin Console Overview
          </h1>
          <p className="text-[#8888aa] text-sm mt-0.5">
            Real-time platform metrics synchronized with PostgreSQL database
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#8888aa] bg-white/5 border border-white/10 px-3 py-1.5 rounded-xl">
          <span className="glow-dot" /> Live DB Sync (30s)
        </div>
      </motion.div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard
              icon={DollarSign}
              label="Total Revenue"
              value={formatPKR(data?.total_revenue)}
              color="emerald"
              subText={`${data?.completed_orders ?? 0} completed orders`}
              onClick={() => navigate("/admin/analytics")}
            />
            <StatCard
              icon={ShoppingBag}
              label="Total Orders"
              value={data?.total_orders ?? 0}
              color="primary"
              subText={`${data?.pending_orders ?? 0} pending processing`}
              onClick={() => navigate("/admin/orders")}
            />
            <StatCard
              icon={Users}
              label="Platform Users"
              value={data?.total_users ?? 0}
              color="purple"
              subText={`${data?.total_customers ?? 0} customer profiles`}
              onClick={() => navigate("/admin/users")}
            />
            <StatCard
              icon={Package}
              label="Catalog Products"
              value={data?.total_products ?? 0}
              color="sky"
              subText={`${data?.low_stock_products_count ?? 0} low stock alerts`}
              onClick={() => navigate("/admin/products")}
            />
            <StatCard
              icon={Ticket}
              label="Open Support Tickets"
              value={data?.open_tickets ?? 0}
              color="amber"
              subText={`${data?.urgent_tickets ?? 0} high/urgent priority`}
              onClick={() => navigate("/admin/tickets")}
            />
            <StatCard
              icon={Bot}
              label="AI Resolution Rate"
              value={`${data?.ai_resolution_rate ?? 0}%`}
              color="emerald"
              subText="Automated issue resolutions"
              onClick={() => navigate("/admin/analytics")}
            />
            <StatCard
              icon={AlertTriangle}
              label="Low / Out of Stock"
              value={(data?.low_stock_products_count ?? 0) + (data?.out_of_stock_products_count ?? 0)}
              color="red"
              subText={`${data?.out_of_stock_products_count ?? 0} completely out of stock`}
              onClick={() => navigate("/admin/products?stock_status=low_stock")}
            />
            <StatCard
              icon={CheckCircle}
              label="Resolved Tickets"
              value={data?.resolved_tickets ?? 0}
              color="emerald"
              subText="Resolved by AI / Support"
              onClick={() => navigate("/admin/tickets")}
            />
          </>
        )}
      </div>

      {/* Analytics Charts Row */}
      {!isLoading && data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Revenue Chart */}
          <motion.div variants={staggerItem} className="lg:col-span-2 card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-[color:var(--color-text)]">Revenue Trend (Last 7 Days)</h2>
                <p className="text-xs text-[#8888aa]">Computed from actual database checkout records</p>
              </div>
              <Link to="/admin/analytics" className="text-xs text-primary-400 hover:underline flex items-center gap-1">
                Analytics <ArrowRight size={12} />
              </Link>
            </div>
            {data.revenue_by_day.some((d) => d.revenue > 0) ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={data.revenue_by_day} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#8888aa" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#8888aa" }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="revenue" name="Revenue (PKR)" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorRev)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-xs text-[#8888aa]">
                No completed order revenue in the past 7 days
              </div>
            )}
          </motion.div>

          {/* Order Status Distribution */}
          <motion.div variants={staggerItem} className="card p-5 flex flex-col">
            <h2 className="text-sm font-semibold text-[color:var(--color-text)] mb-1">Order Status Distribution</h2>
            <p className="text-xs text-[#8888aa] mb-4">Breakdown of customer orders</p>
            {data.order_status_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={data.order_status_distribution} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                    {data.order_status_distribution.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend iconSize={9} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex-1 flex items-center justify-center text-xs text-[#8888aa]">No order status records yet</div>
            )}
          </motion.div>
        </div>
      )}

      {/* Data Streams Row */}
      {!isLoading && data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Recent Customer Orders */}
          <motion.div variants={staggerItem} className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
                <ShoppingBag size={16} className="text-primary-400" /> Recent Orders
              </h2>
              <Link to="/admin/orders" className="text-xs text-primary-400 hover:underline">
                View All ({data.total_orders})
              </Link>
            </div>
            {data.recent_orders.length > 0 ? (
              <div className="divide-y divide-white/5 text-xs">
                {data.recent_orders.map((o) => (
                  <div
                    key={o.id}
                    onClick={() => navigate(`/admin/orders/${o.id}`)}
                    className="py-2.5 flex items-center justify-between hover:bg-white/5 px-2 rounded-lg cursor-pointer transition-colors"
                  >
                    <div>
                      <p className="font-semibold text-[color:var(--color-text)]">{o.order_number}</p>
                      <p className="text-[#8888aa] text-[11px]">{o.customer_name} ({o.item_count} items)</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-primary-300">PKR {Number(o.total_amount).toLocaleString()}</p>
                      <span className="inline-block px-2 py-0.5 rounded-md text-[10px] uppercase font-semibold bg-primary-500/15 text-primary-300">
                        {o.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-[#8888aa] py-6 text-center">No customer orders recorded yet.</p>
            )}
          </motion.div>

          {/* Low Stock Alerts */}
          <motion.div variants={staggerItem} className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-400" /> Low Stock Alerts
              </h2>
              <Link to="/admin/products" className="text-xs text-primary-400 hover:underline">
                Manage Catalog
              </Link>
            </div>
            {data.low_stock_products.length > 0 ? (
              <div className="divide-y divide-white/5 text-xs">
                {data.low_stock_products.map((p) => (
                  <div
                    key={p.id}
                    onClick={() => navigate(`/admin/products/${p.id}`)}
                    className="py-2.5 flex items-center justify-between hover:bg-white/5 px-2 rounded-lg cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {p.primary_image_url ? (
                        <img src={p.primary_image_url} alt={p.name} className="w-8 h-8 rounded-lg object-cover bg-white/5" />
                      ) : (
                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-[10px]">📦</div>
                      )}
                      <div>
                        <p className="font-semibold text-[color:var(--color-text)] truncate max-w-[180px]">{p.name}</p>
                        <p className="text-[#8888aa] text-[11px]">SKU: {p.sku}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 rounded-md text-[11px] font-bold ${p.stock === 0 ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"}`}>
                        {p.stock === 0 ? "Out of Stock" : `${p.stock} remaining`}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-[#8888aa] py-6 text-center">All catalog products have sufficient stock.</p>
            )}
          </motion.div>
        </div>
      )}
    </motion.div>
  );
}
