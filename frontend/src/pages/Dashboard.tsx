// src/pages/Dashboard.tsx
// Role-aware main dashboard — customer / support / admin

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle,
  Clock,
  DollarSign,
  Package,
  ShoppingBag,
  Ticket,
  TrendingUp,
} from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import { stagger, staggerItem } from "../animations/variants";
import { SkeletonCard } from "../components/ui/Skeleton";
import useAuth from "../hooks/useAuth";
import dashboardService from "../services/dashboard.service";
import ordersService from "../services/orders.service";
import productsService from "../services/products.service";
import ticketsService from "../services/tickets.service";

const fmt = (n?: number | null, fallback = "0") =>
  n != null ? n.toLocaleString() : fallback;

const fmtSecs = (s?: number | null) => {
  if (!s) return "—";
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  return `${(s / 3600).toFixed(1)}h`;
};

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color = "primary",
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color?: "primary" | "emerald" | "amber" | "red" | "sky";
}) {
  const colors = {
    primary: "bg-primary-500/10 text-primary-400 border-primary-500/20",
    emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    amber: "bg-amber-500/10  text-amber-400  border-amber-500/20",
    red: "bg-red-500/10    text-red-400    border-red-500/20",
    sky: "bg-sky-500/10    text-sky-400    border-sky-500/20",
  };
  return (
    <motion.div variants={staggerItem} className="card p-5 card-hover">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-9 h-9 rounded-xl border flex items-center justify-center ${colors[color]}`}>
          <Icon size={16} />
        </div>
      </div>
      <p className="text-2xl font-bold text-[color:var(--color-text)]">{value}</p>
      <p className="text-xs text-[#8888aa] mt-0.5">{label}</p>
      {sub && <p className="text-xs text-emerald-400 mt-1">{sub}</p>}
    </motion.div>
  );
}

// ── Customer Dashboard ────────────────────────────────────────────────────────
function CustomerDashboard() {
  const { user } = useAuth();
  const { data: ordersData, isLoading: ordersLoading } = useQuery({
    queryKey: ["orders", { page: 1, per_page: 5 }],
    queryFn: () => ordersService.list({ page: 1, per_page: 5 }),
  });

  const { data: ticketsData } = useQuery({
    queryKey: ["my-tickets", { page: 1 }],
    queryFn: () => ticketsService.listMine({ page: 1, per_page: 5 }),
  });

  const { data: productsData } = useQuery({
    queryKey: ["products-recommended"],
    queryFn: () => productsService.list({ page: 1, per_page: 4 }),
  });

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  // Calculate real total spent by customer
  const totalSpent = ordersData?.items.reduce((sum, o) => sum + Number(o.total_amount), 0) || 0;
  const activeOrdersCount = ordersData?.items.filter((o) => !["delivered", "cancelled"].includes(o.status)).length || 0;

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Header */}
      <motion.div variants={staggerItem} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
            {greeting}, {user?.full_name?.split(" ")[0]} 👋
          </h1>
          <p className="text-[#8888aa] text-sm mt-1">
            Welcome back to CommerceFlow AI customer portal
          </p>
        </div>
        <Link
          to="/chat"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-500 to-accent-500 text-white text-xs font-semibold shadow-glow-sm hover:opacity-95 transition-all w-fit"
        >
          <Bot size={16} /> Ask CommerceFlow AI
        </Link>
      </motion.div>

      {/* Real Statistics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {ordersLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard icon={ShoppingBag} label="Total Orders" value={fmt(ordersData?.total)} color="sky" />
            <StatCard icon={DollarSign} label="Total Spent" value={`PKR ${totalSpent.toLocaleString()}`} color="emerald" />
            <StatCard icon={Package} label="Active Orders" value={fmt(activeOrdersCount)} color="primary" />
            <StatCard icon={Ticket} label="Open Support Tickets" value={fmt(ticketsData?.items.filter((t) => !["closed", "resolved"].includes(t.status)).length)} color="amber" />
          </>
        )}
      </div>

      {/* Quick Nav Cards */}
      <motion.div variants={staggerItem} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link to="/chat" className="card p-5 card-hover flex items-center gap-4 group">
          <div className="w-10 h-10 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-primary-500/20 transition-colors">
            <Bot size={18} className="text-primary-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[color:var(--color-text)]">Ask AI Assistant</p>
            <p className="text-xs text-[#8888aa]">Instant product & order support</p>
          </div>
        </Link>
        <Link to="/orders" className="card p-5 card-hover flex items-center gap-4 group">
          <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-sky-500/20 transition-colors">
            <ShoppingBag size={18} className="text-sky-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[color:var(--color-text)]">My Orders</p>
            <p className="text-xs text-[#8888aa]">Track & view order details</p>
          </div>
        </Link>
        <Link to="/my/tickets" className="card p-5 card-hover flex items-center gap-4 group">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-amber-500/20 transition-colors">
            <Ticket size={18} className="text-amber-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[color:var(--color-text)]">Support Desk</p>
            <p className="text-xs text-[#8888aa]">Manage your support tickets</p>
          </div>
        </Link>
      </motion.div>

      {/* Recent Customer Orders */}
      <motion.div variants={staggerItem} className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
            <ShoppingBag size={16} className="text-primary-400" /> Recent Orders
          </h2>
          <Link to="/orders" className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1">
            View all ({ordersData?.total ?? 0}) <ArrowRight size={12} />
          </Link>
        </div>
        {ordersLoading ? (
          <div className="p-5"><SkeletonCard /></div>
        ) : ordersData?.items.length === 0 ? (
          <div className="p-8 text-center text-[#8888aa] text-xs space-y-2">
            <p>You haven't placed any orders yet.</p>
            <Link to="/products" className="btn-primary text-xs inline-block">Browse Catalog</Link>
          </div>
        ) : (
          <div className="divide-y divide-white/5 text-xs">
            {ordersData?.items.slice(0, 5).map((order) => (
              <Link
                key={order.id}
                to={`/orders/${order.id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-white/5 transition-colors"
              >
                <div>
                  <p className="font-semibold text-primary-300">{order.order_number}</p>
                  <p className="text-[#8888aa] text-[11px]">
                    {new Date(order.created_at).toLocaleDateString()} · {order.item_count} item{order.item_count !== 1 ? "s" : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-[color:var(--color-text)]">PKR {Number(order.total_amount).toLocaleString()}</p>
                  <span className="inline-block px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-white/10 text-white">
                    {order.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </motion.div>

      {/* Recommended Products */}
      {productsData?.items && productsData.items.length > 0 && (
        <motion.div variants={staggerItem} className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
              <Package size={16} className="text-sky-400" /> Recommended Products
            </h2>
            <Link to="/products" className="text-xs text-primary-400 hover:underline">
              View Catalog
            </Link>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {productsData.items.map((prod) => (
              <Link
                key={prod.id}
                to={`/products/${prod.id}`}
                className="card p-3 card-hover space-y-2 group"
              >
                <div className="aspect-square rounded-xl overflow-hidden bg-white/5 border border-white/10">
                  {prod.images.length > 0 || prod.image_url ? (
                    <img
                      src={prod.images[0]?.image_url || prod.image_url}
                      alt={prod.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xl">📦</div>
                  )}
                </div>
                <p className="text-xs font-semibold text-[color:var(--color-text)] truncate">{prod.name}</p>
                <p className="text-xs font-bold text-primary-400">PKR {Number(prod.price).toLocaleString()}</p>
              </Link>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}

// ── Support Dashboard ─────────────────────────────────────────────────────────
function SupportDashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => dashboardService.getSupportStats(),
    refetchInterval: 30_000,
  });

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      <motion.div variants={staggerItem}>
        <h1 className="text-2xl font-bold text-[color:var(--color-text)]">Support Center Dashboard</h1>
        <p className="text-[#8888aa] text-sm mt-1">Live customer support ticket queues</p>
      </motion.div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard icon={Ticket} label="Open Tickets" value={fmt(stats?.open_tickets)} color="sky" />
            <StatCard icon={Clock} label="Assigned to Team" value={fmt(stats?.assigned_tickets)} color="primary" />
            <StatCard icon={AlertTriangle} label="Urgent Priority" value={fmt(stats?.urgent_tickets)} color="red" />
            <StatCard icon={CheckCircle} label="Resolved Today" value={fmt(stats?.resolved_today)} color="emerald" />
            <StatCard icon={TrendingUp} label="AI Resolution %" value={stats?.ai_resolution_percent != null ? `${stats.ai_resolution_percent.toFixed(1)}%` : "—"} color="primary" />
            <StatCard icon={Clock} label="Avg Response" value={fmtSecs(stats?.average_response_time_seconds)} color="sky" />
            <StatCard icon={Clock} label="Avg Resolution" value={fmtSecs(stats?.average_resolution_time_seconds)} color="amber" />
            <StatCard icon={Ticket} label="Total Tickets" value={fmt(stats?.total_tickets)} color="primary" />
          </>
        )}
      </div>

      <motion.div variants={staggerItem} className="card p-5">
        <h2 className="text-sm font-semibold text-[color:var(--color-text)] mb-4">Support Navigation</h2>
        <div className="flex flex-wrap gap-3">
          <Link to="/support/tickets" className="btn-primary text-sm">All Support Tickets</Link>
          <Link to="/support/queue" className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10 text-sm text-[color:var(--color-text)] hover:bg-white/5 transition-colors">My Assigned Queue</Link>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Root Dashboard — role router ──────────────────────────────────────────────
export default function Dashboard() {
  const { user } = useAuth();

  if (user?.role === "admin") {
    return <Navigate to="/admin/dashboard" replace />;
  }

  if (user?.role === "support") {
    return <SupportDashboard />;
  }

  return <CustomerDashboard />;
}
