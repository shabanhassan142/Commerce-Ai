// src/pages/Cart.tsx
// Shopping Cart page with item editing, quantity controls, line subtotals, and summary

import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Minus, Package, Plus, ShoppingCart, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import useAuth from "../hooks/useAuth";
import cartService, { type CartItem } from "../services/cart.service";

export default function Cart() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<CartItem[]>([]);

  useEffect(() => {
    if (user?.id) {
      setItems(cartService.getCart(user.id));
    }
  }, [user?.id]);

  const updateQty = (productId: string, newQty: number) => {
    if (!user?.id) return;
    const updated = cartService.updateQuantity(user.id, productId, newQty);
    setItems(updated);
  };

  const removeItem = (productId: string) => {
    if (!user?.id) return;
    const updated = cartService.removeFromCart(user.id, productId);
    setItems(updated);
    toast.info("Item removed from cart");
  };

  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const shipping = subtotal >= 50 || subtotal === 0 ? 0 : 5.0;
  const total = subtotal + shipping;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-2.5">
            <ShoppingCart className="text-primary-400" size={24} />
            Shopping Cart
          </h1>
          <p className="text-xs text-[#8888aa] mt-1">Review your selected items before checkout</p>
        </div>
        <button
          onClick={() => navigate("/products")}
          className="flex items-center gap-2 text-xs font-semibold text-[#8888aa] hover:text-white px-3 py-2 rounded-xl bg-white/5 border border-white/10 transition-colors"
        >
          <ArrowLeft size={14} /> Continue Shopping
        </button>
      </div>

      {items.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-12 text-center flex flex-col items-center justify-center gap-4"
        >
          <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-[#8888aa]">
            <Package size={32} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[color:var(--color-text)]">Your cart is empty</h2>
            <p className="text-xs text-[#8888aa] mt-1">Explore our catalog to add products to your cart.</p>
          </div>
          <button
            onClick={() => navigate("/products")}
            className="mt-2 px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-medium text-sm transition-colors flex items-center gap-2"
          >
            Browse Products <ArrowRight size={16} />
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Cart items list */}
          <div className="lg:col-span-2 space-y-3">
            {items.map((item) => (
              <motion.div
                key={item.product_id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-16 h-16 rounded-xl bg-[#1a1a2e] overflow-hidden flex-shrink-0 border border-white/10">
                    {item.image_url ? (
                      <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#8888aa]">
                        <Package size={20} />
                      </div>
                    )}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-sm text-[color:var(--color-text)] truncate">{item.name}</h3>
                    {item.brand && <p className="text-xs text-[#8888aa]">by {item.brand}</p>}
                    <p className="text-xs text-primary-400 font-medium mt-1">${item.price.toFixed(2)} each</p>
                  </div>
                </div>

                {/* Quantity + Subtotal + Actions */}
                <div className="flex items-center justify-between sm:justify-end gap-6 w-full sm:w-auto pt-2 sm:pt-0 border-t sm:border-0 border-white/5">
                  <div className="flex items-center border border-white/10 rounded-lg bg-white/5 px-2 py-1">
                    <button
                      onClick={() => updateQty(item.product_id, item.quantity - 1)}
                      className="p-1 text-[#8888aa] hover:text-white"
                      aria-label="Decrease quantity"
                    >
                      <Minus size={13} />
                    </button>
                    <span className="text-xs font-semibold text-[color:var(--color-text)] px-3">{item.quantity}</span>
                    <button
                      onClick={() => updateQty(item.product_id, item.quantity + 1)}
                      disabled={item.quantity >= item.stock}
                      className="p-1 text-[#8888aa] hover:text-white disabled:opacity-30"
                      aria-label="Increase quantity"
                    >
                      <Plus size={13} />
                    </button>
                  </div>

                  <span className="font-bold text-sm text-[color:var(--color-text)] w-20 text-right">
                    ${(item.price * item.quantity).toFixed(2)}
                  </span>

                  <button
                    onClick={() => removeItem(item.product_id)}
                    className="p-2 text-[#8888aa] hover:text-red-400 transition-colors"
                    aria-label="Remove item"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Order Summary */}
          <div className="space-y-4">
            <div className="card p-5 space-y-4">
              <h2 className="text-base font-bold text-[color:var(--color-text)] border-b border-white/5 pb-3">Order Summary</h2>

              <div className="space-y-2 text-sm text-[#8888aa]">
                <div className="flex justify-between">
                  <span>Subtotal ({items.reduce((sum, i) => sum + i.quantity, 0)} items)</span>
                  <span className="text-[color:var(--color-text)] font-semibold">${subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Shipping</span>
                  <span className="text-[color:var(--color-text)] font-semibold">
                    {shipping === 0 ? <span className="text-emerald-400 font-bold uppercase text-xs">FREE</span> : `$${shipping.toFixed(2)}`}
                  </span>
                </div>
                {subtotal < 50 && subtotal > 0 && (
                  <p className="text-[11px] text-primary-400">Add ${(50 - subtotal).toFixed(2)} more for FREE shipping!</p>
                )}
              </div>

              <div className="border-t border-white/5 pt-3 flex justify-between items-center text-base font-bold text-[color:var(--color-text)]">
                <span>Total</span>
                <span className="text-xl text-primary-300">${total.toFixed(2)}</span>
              </div>

              <button
                onClick={() => navigate("/checkout")}
                className="w-full py-3 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-semibold text-sm transition-colors shadow-lg shadow-primary-500/20 flex items-center justify-center gap-2"
              >
                Proceed to Checkout <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
