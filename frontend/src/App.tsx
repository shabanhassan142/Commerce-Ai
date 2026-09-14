// src/App.tsx
// Root application with full routing, auth provider, and query client

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Bot } from "lucide-react";
import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./contexts/AuthContext";
import useAuth from "./hooks/useAuth";
import DashboardLayout from "./layouts/DashboardLayout";

// ── Eager-loaded pages (auth + landing) ─────────────────────────────────────
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";

// ── Lazy-loaded pages ─────────────────────────────────────────────────────────
const Dashboard              = lazy(() => import("./pages/Dashboard"));
const Chat                   = lazy(() => import("./pages/Chat"));
const Products               = lazy(() => import("./pages/Products"));
const ProductDetail          = lazy(() => import("./pages/ProductDetail"));
const Cart                   = lazy(() => import("./pages/Cart"));
const Checkout               = lazy(() => import("./pages/Checkout"));
const OrderConfirmation      = lazy(() => import("./pages/OrderConfirmation"));
const Orders                 = lazy(() => import("./pages/Orders"));
const OrderDetail            = lazy(() => import("./pages/OrderDetail"));
const CustomerTickets        = lazy(() => import("./pages/CustomerTickets"));
const CustomerTicketDetail   = lazy(() => import("./pages/CustomerTicketDetail"));
const SupportDashboard       = lazy(() => import("./pages/SupportDashboard"));
const SupportTickets         = lazy(() => import("./pages/SupportTickets"));
const TicketWorkspace        = lazy(() => import("./pages/TicketWorkspace"));
const AdminDashboard         = lazy(() => import("./pages/AdminDashboard"));
const AdminUsers             = lazy(() => import("./pages/AdminUsers"));
const AdminUserDetail        = lazy(() => import("./pages/AdminUserDetail"));
const AdminProducts          = lazy(() => import("./pages/AdminProducts"));
const AdminProductDetail     = lazy(() => import("./pages/AdminProductDetail"));
const AdminOrders            = lazy(() => import("./pages/AdminOrders"));
const AdminOrderDetail       = lazy(() => import("./pages/AdminOrderDetail"));
const AdminAnalytics         = lazy(() => import("./pages/AdminAnalytics"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 3,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// ── Page loading fallback ─────────────────────────────────────────────────────
function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4">
      <div className="w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      <p className="text-[#8888aa] text-sm">Loading…</p>
    </div>
  );
}

// ── Auth guards ───────────────────────────────────────────────────────────────
function ProtectedRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--color-bg)" }}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow-md">
            <Bot size={20} className="text-white" />
          </div>
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (roles && user && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return null;
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <>{children}</>;
}

// ── Wrapped page in layout ────────────────────────────────────────────────────
function LayoutPage({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  return (
    <ProtectedRoute roles={roles}>
      <DashboardLayout>
        <Suspense fallback={<PageLoader />}>
          {children}
        </Suspense>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

// ── Animated Routes ───────────────────────────────────────────────────────────
function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* ── Public ──────────────────────────────────────────────────────── */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

        {/* ── Shared protected ─────────────────────────────────────────────── */}
        <Route path="/dashboard" element={<LayoutPage><Dashboard /></LayoutPage>} />

        {/* ── Customer ─────────────────────────────────────────────────────── */}
        <Route path="/chat"                element={<LayoutPage><Chat /></LayoutPage>} />
        <Route path="/products"            element={<LayoutPage><Products /></LayoutPage>} />
        <Route path="/products/:id"        element={<LayoutPage><ProductDetail /></LayoutPage>} />
        <Route path="/cart"                element={<LayoutPage roles={["customer"]}><Cart /></LayoutPage>} />
        <Route path="/checkout"            element={<LayoutPage roles={["customer"]}><Checkout /></LayoutPage>} />
        <Route path="/orders/confirmation/:id" element={<LayoutPage roles={["customer"]}><OrderConfirmation /></LayoutPage>} />
        <Route path="/orders"              element={<LayoutPage><Orders /></LayoutPage>} />
        <Route path="/orders/:id"          element={<LayoutPage><OrderDetail /></LayoutPage>} />
        <Route path="/my/tickets"          element={<LayoutPage roles={["customer"]}><CustomerTickets /></LayoutPage>} />
        <Route path="/my/tickets/:id"      element={<LayoutPage roles={["customer"]}><CustomerTicketDetail /></LayoutPage>} />

        {/* ── Support ──────────────────────────────────────────────────────── */}
        <Route path="/support/dashboard"   element={<LayoutPage roles={["support","admin"]}><SupportDashboard /></LayoutPage>} />
        <Route path="/support/tickets"     element={<LayoutPage roles={["support","admin"]}><SupportTickets /></LayoutPage>} />
        <Route path="/support/queue"       element={<LayoutPage roles={["support","admin"]}><SupportTickets /></LayoutPage>} />
        <Route path="/support/tickets/:id" element={<LayoutPage roles={["support","admin"]}><TicketWorkspace /></LayoutPage>} />

        {/* ── Admin ────────────────────────────────────────────────────────── */}
        <Route path="/admin/dashboard"     element={<LayoutPage roles={["admin"]}><AdminDashboard /></LayoutPage>} />
        <Route path="/admin/users"         element={<LayoutPage roles={["admin"]}><AdminUsers /></LayoutPage>} />
        <Route path="/admin/users/:id"     element={<LayoutPage roles={["admin"]}><AdminUserDetail /></LayoutPage>} />
        <Route path="/admin/products"      element={<LayoutPage roles={["admin"]}><AdminProducts /></LayoutPage>} />
        <Route path="/admin/products/:id"  element={<LayoutPage roles={["admin"]}><AdminProductDetail /></LayoutPage>} />
        <Route path="/admin/orders"        element={<LayoutPage roles={["admin"]}><AdminOrders /></LayoutPage>} />
        <Route path="/admin/orders/:id"    element={<LayoutPage roles={["admin"]}><AdminOrderDetail /></LayoutPage>} />
        <Route path="/admin/tickets"       element={<LayoutPage roles={["admin"]}><SupportTickets /></LayoutPage>} />
        <Route path="/admin/tickets/:id"   element={<LayoutPage roles={["admin"]}><TicketWorkspace /></LayoutPage>} />
        <Route path="/admin/analytics"     element={<LayoutPage roles={["admin"]}><AdminAnalytics /></LayoutPage>} />
        <Route path="/admin/*"             element={<LayoutPage roles={["admin"]}><AdminDashboard /></LayoutPage>} />

        {/* ── Role redirect shortcuts ──────────────────────────────────────── */}
        <Route path="/tickets"             element={<Navigate to="/my/tickets" replace />} />
        <Route path="/analytics"           element={<Navigate to="/admin/analytics" replace />} />
        <Route path="/settings"            element={<LayoutPage><PlaceholderPage title="Settings" /></LayoutPage>} />
        <Route path="/knowledge"           element={<LayoutPage><PlaceholderPage title="Knowledge Base" /></LayoutPage>} />

        {/* ── 404 ──────────────────────────────────────────────────────────── */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center min-h-[60vh] gap-4"
    >
      <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center">
        <Bot size={24} className="text-primary-400" />
      </div>
      <h2 className="text-xl font-bold text-[color:var(--color-text)]">{title}</h2>
      <p className="text-[#8888aa] text-sm">Coming soon</p>
    </motion.div>
  );
}

// ── Root App ──────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AnimatedRoutes />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text)",
              fontSize: "14px",
            },
          }}
        />
      </AuthProvider>
    </QueryClientProvider>
  );
}
