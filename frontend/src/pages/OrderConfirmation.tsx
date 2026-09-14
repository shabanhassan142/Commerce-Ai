// src/pages/OrderConfirmation.tsx
// Order confirmation page rendered upon successful checkout

import { motion } from "framer-motion";
import { CheckCircle2, Clock, Package, ShoppingBag, Truck } from "lucide-react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

export default function OrderConfirmation() {
  useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const order = location.state?.order;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="card p-8 text-center space-y-4 border border-emerald-500/20 bg-emerald-500/5"
      >
        <div className="w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto shadow-glow-sm">
          <CheckCircle2 size={36} />
        </div>

        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)]">Order Placed Successfully!</h1>
          <p className="text-xs text-[#8888aa] mt-1">
            Thank you for your demo purchase. Your order has been recorded in the database.
          </p>
        </div>

        {order && (
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-xs font-mono text-primary-300">
            <span>Order #{order.order_number}</span>
            <span>•</span>
            <span>ID: {order.id?.slice(0, 8)}…</span>
          </div>
        )}
      </motion.div>

      {/* Order Details Card */}
      {order ? (
        <div className="card p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-white/5 pb-4 text-xs">
            <div className="flex items-center gap-2 text-[#8888aa]">
              <Clock size={14} />
              <span>Status: <strong className="text-emerald-400 uppercase">{order.status}</strong></span>
            </div>
            <div className="flex items-center gap-2 text-[#8888aa]">
              <Truck size={14} />
              <span>Payment: <strong className="text-primary-300 uppercase">{order.payment?.method ?? "Demo Card"}</strong></span>
            </div>
          </div>

          {/* Items */}
          <div className="space-y-3">
            <h2 className="text-sm font-bold text-[color:var(--color-text)]">Purchased Items</h2>
            <div className="space-y-2">
              {order.items?.map((item: any) => (
                <div key={item.id} className="flex items-center justify-between p-3 rounded-xl bg-white/3 border border-white/6 text-xs">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-[#1a1a2e] flex items-center justify-center text-[#8888aa] border border-white/10">
                      {item.product_image ? (
                        <img src={item.product_image} alt="" className="w-full h-full object-cover rounded-lg" />
                      ) : (
                        <Package size={16} />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-[color:var(--color-text)]">{item.product_name ?? "Product"}</p>
                      <p className="text-[#8888aa]">Qty: {item.quantity} × ${Number(item.unit_price).toFixed(2)}</p>
                    </div>
                  </div>
                  <span className="font-bold text-[color:var(--color-text)]">${Number(item.total_price).toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Total summary */}
          <div className="border-t border-white/5 pt-4 flex justify-between items-center text-sm font-bold">
            <span className="text-[color:var(--color-text)]">Total Amount Paid</span>
            <span className="text-xl text-primary-300">${Number(order.total_amount).toFixed(2)}</span>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button
              onClick={() => navigate("/orders")}
              className="flex-1 py-3 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-semibold text-sm transition-colors text-center flex items-center justify-center gap-2"
            >
              <ShoppingBag size={16} /> View My Orders
            </button>
            <button
              onClick={() => navigate("/products")}
              className="py-3 px-6 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold text-sm transition-colors text-center"
            >
              Continue Shopping
            </button>
          </div>
        </div>
      ) : (
        <div className="text-center py-6">
          <button
            onClick={() => navigate("/orders")}
            className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-medium text-sm"
          >
            View All Orders
          </button>
        </div>
      )}
    </div>
  );
}
