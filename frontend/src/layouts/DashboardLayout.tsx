// src/layouts/DashboardLayout.tsx
// Role-aware sidebar layout with mobile support and theme toggle

import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3,
  Bot,
  ChevronRight,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  Package,
  Settings,
  ShoppingBag,
  ShoppingCart,
  Sun,
  Ticket,
  Users,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import useAuth from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";
import cartService from "../services/cart.service";

// ── Nav config per role ──────────────────────────────────────────────────────
const CUSTOMER_NAV = [
  { icon: LayoutDashboard, label: "Dashboard",  path: "/dashboard" },
  { icon: MessageSquare,   label: "AI Chat",    path: "/chat",     badge: "AI" },
  { icon: Package,         label: "Products",   path: "/products" },
  { icon: ShoppingCart,    label: "Cart",       path: "/cart",     isCart: true },
  { icon: ShoppingBag,     label: "Orders",     path: "/orders" },
  { icon: Ticket,          label: "Support",    path: "/my/tickets" },
];

const SUPPORT_NAV = [
  { icon: LayoutDashboard, label: "Dashboard",  path: "/support/dashboard" },
  { icon: Ticket,          label: "All Tickets", path: "/support/tickets" },
  { icon: HelpCircle,      label: "My Queue",   path: "/support/queue" },
];

const ADMIN_NAV = [
  { icon: LayoutDashboard, label: "Admin Home", path: "/admin/dashboard" },
  { icon: BarChart3,       label: "Analytics",  path: "/admin/analytics" },
  { icon: Users,           label: "Users",      path: "/admin/users" },
  { icon: Package,         label: "Products",   path: "/admin/products" },
  { icon: ShoppingBag,     label: "Orders",     path: "/admin/orders" },
  { icon: Ticket,          label: "Tickets",    path: "/admin/tickets" },
];

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, setTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [cartCount, setCartCount] = useState(0);

  useEffect(() => {
    const updateCount = () => {
      setCartCount(cartService.getCartCount(user?.id));
    };
    updateCount();
    window.addEventListener("cart_updated", updateCount);
    return () => window.removeEventListener("cart_updated", updateCount);
  }, [user?.id]);

  const role = user?.role ?? "customer";

  const navItems =
    role === "admin"
      ? ADMIN_NAV
      : role === "support"
      ? SUPPORT_NAV
      : CUSTOMER_NAV;

  const handleLogout = async () => {
    await logout();
    toast.success("Logged out successfully");
    navigate("/login");
  };

  const cycleTheme = () => {
    setTheme(theme === "dark" ? "light" : theme === "light" ? "system" : "dark");
  };

  const ThemeIcon = theme === "light" ? Sun : Moon;

  // Current page breadcrumb
  const currentItem = [...CUSTOMER_NAV, ...SUPPORT_NAV, ...ADMIN_NAV].find(
    (n) => location.pathname === n.path || location.pathname.startsWith(n.path + "/")
  );

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="p-5 border-b border-primary-500/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow-sm">
            <Bot size={16} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-[color:var(--color-text)] text-sm leading-tight">CommerceFlow</p>
            <p className="text-[10px] text-primary-400 font-medium tracking-wider uppercase">AI Platform</p>
          </div>
        </div>
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden p-1 text-[#8888aa] hover:text-white"
          aria-label="Close sidebar"
        >
          <X size={16} />
        </button>
      </div>

      {/* Role badge */}
      <div className="px-4 py-2 border-b border-white/5">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-primary-400">
          {role === "admin" ? "Admin Console" : role === "support" ? "Support Center" : "Customer Portal"}
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto" aria-label="Main navigation">
        {navItems.map(({ icon: Icon, label, path, badge, isCart }: typeof navItems[0] & { badge?: string; isCart?: boolean }) => (
          <NavLink
            key={path}
            to={path}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group ${
                isActive
                  ? "bg-primary-500/15 text-primary-300 border border-primary-500/25"
                  : "text-[#8888aa] hover:text-[color:var(--color-text)] hover:bg-white/5"
              }`
            }
          >
            <Icon size={16} className="flex-shrink-0" />
            <span className="flex-1">{label}</span>
            {isCart && cartCount > 0 && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                {cartCount}
              </span>
            )}
            {badge && !isCart && (
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-primary-500/20 text-primary-400 tracking-wide">
                {badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User + actions */}
      <div className="p-4 border-t border-white/5 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-primary-500/20 border border-primary-500/30 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-bold text-primary-400">
              {user?.full_name?.charAt(0)?.toUpperCase() ?? "U"}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-[color:var(--color-text)] truncate">{user?.full_name}</p>
            <p className="text-[10px] text-[#8888aa] capitalize truncate">{user?.role} · {user?.email}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={cycleTheme}
            className="flex-1 flex items-center justify-center gap-1.5 text-[#8888aa] hover:text-[color:var(--color-text)] text-xs py-1.5 rounded-lg hover:bg-white/5 transition-colors"
            aria-label="Toggle theme"
            title={`Theme: ${theme}`}
          >
            <ThemeIcon size={13} />
            <span className="capitalize">{theme}</span>
          </button>
          <NavLink
            to="/settings"
            className="flex-1 flex items-center justify-center gap-1.5 text-[#8888aa] hover:text-[color:var(--color-text)] text-xs py-1.5 rounded-lg hover:bg-white/5 transition-colors"
          >
            <Settings size={13} /> Settings
          </NavLink>
          <button
            onClick={handleLogout}
            className="flex-1 flex items-center justify-center gap-1.5 text-[#8888aa] hover:text-red-400 text-xs py-1.5 rounded-lg hover:bg-red-500/5 transition-colors"
            aria-label="Logout"
          >
            <LogOut size={13} /> Logout
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen" style={{ background: "var(--color-bg)" }}>
      {/* ── Desktop Sidebar ────────────────────────────────────────────────────── */}
      <aside className="hidden lg:flex w-60 flex-shrink-0 flex-col glass border-r border-primary-500/10 sticky top-0 h-screen">
        <SidebarContent />
      </aside>

      {/* ── Mobile Overlay ─────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed left-0 top-0 bottom-0 w-64 z-50 glass border-r border-primary-500/10 flex flex-col lg:hidden"
            >
              <SidebarContent />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* ── Main Area ─────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header
          className="h-14 flex items-center justify-between px-4 md:px-6 border-b sticky top-0 z-30 glass"
          style={{ borderColor: "var(--color-border)" }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded-lg text-[#8888aa] hover:text-[color:var(--color-text)] hover:bg-white/5"
              aria-label="Open menu"
            >
              <Menu size={18} />
            </button>
            <div className="flex items-center gap-1.5 text-sm text-[#8888aa]">
              <span className="hidden sm:block">CommerceFlow AI</span>
              <ChevronRight size={13} className="hidden sm:block" />
              <span className="text-[color:var(--color-text)] font-medium">
                {currentItem?.label ?? "Dashboard"}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="glow-dot" />
            <span className="text-xs text-[#8888aa] hidden sm:block">System Online</span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 md:p-6 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
