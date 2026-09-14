// src/pages/Checkout.tsx
// Checkout page for order placement with explicit demo/test payment mode
import { ArrowLeft, CheckCircle2, CreditCard, ShieldCheck, ShoppingBag, Truck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import useAuth from "../hooks/useAuth";
import api from "../services/api";
import cartService from "../services/cart.service";

export default function Checkout() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const cart = user?.id ? cartService.getCart(user.id) : [];

  const [address, setAddress] = useState({
    street: "123 Tech Boulevard",
    city: "San Francisco",
    state: "CA",
    postal_code: "94107",
    country: "USA",
  });

  const [paymentMethod, setPaymentMethod] = useState<"card" | "cod">("card");

  const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const shipping = subtotal >= 50 || subtotal === 0 ? 0 : 5.0;
  const total = subtotal + shipping;

  if (cart.length === 0) {
    return (
      <div className="card p-12 text-center max-w-lg mx-auto space-y-4">
        <ShoppingBag className="mx-auto text-[#8888aa]" size={40} />
        <h2 className="text-lg font-bold text-[color:var(--color-text)]">Your cart is empty</h2>
        <p className="text-xs text-[#8888aa]">Add products to your cart before proceeding to checkout.</p>
        <button
          onClick={() => navigate("/products")}
          className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-medium text-sm"
        >
          Browse Products
        </button>
      </div>
    );
  }

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.id) return;

    setSubmitting(true);
    try {
      const payload = {
        items: cart.map((i) => ({
          product_id: i.product_id,
          quantity: i.quantity,
        })),
        shipping_address: address,
        payment_method: paymentMethod,
      };

      const res = await api.post("/api/v1/orders", payload);
      const createdOrder = res.data;

      // Clear cart on successful order
      cartService.clearCart(user.id);

      toast.success("Order placed successfully!");
      navigate(`/orders/confirmation/${createdOrder.id}`, {
        state: { order: createdOrder },
      });
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail ?? err.message ?? "Failed to place order.";
      toast.error(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate("/cart")}
          className="flex items-center gap-2 text-xs font-semibold text-[#8888aa] hover:text-white px-3 py-2 rounded-xl bg-white/5 border border-white/10"
        >
          <ArrowLeft size={14} /> Back to Cart
        </button>
        <div className="flex items-center gap-2 text-xs text-emerald-400 font-semibold px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
          <ShieldCheck size={14} /> Secure Checkout
        </div>
      </div>

      <form onSubmit={handlePlaceOrder} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main form details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Customer info */}
          <div className="card p-5 space-y-4">
            <h2 className="text-base font-bold text-[color:var(--color-text)] flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary-500/20 text-primary-400 text-xs font-bold flex items-center justify-center">1</span>
              Customer Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <div>
                <label className="text-xs text-[#8888aa] block mb-1">Full Name</label>
                <input
                  type="text"
                  value={user?.full_name ?? ""}
                  disabled
                  className="input-field opacity-75 cursor-not-allowed"
                />
              </div>
              <div>
                <label className="text-xs text-[#8888aa] block mb-1">Email Address</label>
                <input
                  type="email"
                  value={user?.email ?? ""}
                  disabled
                  className="input-field opacity-75 cursor-not-allowed"
                />
              </div>
            </div>
          </div>

          {/* Shipping Address */}
          <div className="card p-5 space-y-4">
            <h2 className="text-base font-bold text-[color:var(--color-text)] flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary-500/20 text-primary-400 text-xs font-bold flex items-center justify-center">2</span>
              Shipping Address
            </h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-[#8888aa] block mb-1">Street Address</label>
                <input
                  type="text"
                  required
                  value={address.street}
                  onChange={(e) => setAddress({ ...address, street: e.target.value })}
                  className="input-field"
                  placeholder="Street Address"
                />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-[#8888aa] block mb-1">City</label>
                  <input
                    type="text"
                    required
                    value={address.city}
                    onChange={(e) => setAddress({ ...address, city: e.target.value })}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="text-xs text-[#8888aa] block mb-1">State / Province</label>
                  <input
                    type="text"
                    required
                    value={address.state}
                    onChange={(e) => setAddress({ ...address, state: e.target.value })}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="text-xs text-[#8888aa] block mb-1">Postal Code</label>
                  <input
                    type="text"
                    required
                    value={address.postal_code}
                    onChange={(e) => setAddress({ ...address, postal_code: e.target.value })}
                    className="input-field"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Demo Payment Notice */}
          <div className="card p-5 space-y-4 border border-primary-500/20 bg-primary-500/5">
            <h2 className="text-base font-bold text-[color:var(--color-text)] flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary-500/20 text-primary-400 text-xs font-bold flex items-center justify-center">3</span>
              Payment Method (Demo Mode)
            </h2>

            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-2.5">
              <CreditCard className="flex-shrink-0 mt-0.5" size={16} />
              <div>
                <p className="font-semibold">Demo / Simulated Checkout</p>
                <p className="text-amber-300/80 mt-0.5">
                  This is a test environment. No real credit card or payment gateway is integrated. Placing an order will simulate a successful transaction securely.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setPaymentMethod("card")}
                className={`p-3.5 rounded-xl border text-left flex items-center gap-3 transition-all ${
                  paymentMethod === "card"
                    ? "bg-primary-500/15 border-primary-500 text-white"
                    : "bg-white/5 border-white/10 text-[#8888aa] hover:border-white/20"
                }`}
              >
                <CreditCard size={18} className={paymentMethod === "card" ? "text-primary-400" : ""} />
                <div>
                  <p className="text-xs font-semibold">Demo Test Card</p>
                  <p className="text-[10px] opacity-75">Simulated Instant Payment</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setPaymentMethod("cod")}
                className={`p-3.5 rounded-xl border text-left flex items-center gap-3 transition-all ${
                  paymentMethod === "cod"
                    ? "bg-primary-500/15 border-primary-500 text-white"
                    : "bg-white/5 border-white/10 text-[#8888aa] hover:border-white/20"
                }`}
              >
                <Truck size={18} className={paymentMethod === "cod" ? "text-primary-400" : ""} />
                <div>
                  <p className="text-xs font-semibold">Cash on Delivery (COD)</p>
                  <p className="text-[10px] opacity-75">Pay upon delivery</p>
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar Summary */}
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <h2 className="text-base font-bold text-[color:var(--color-text)] border-b border-white/5 pb-3">Items Summary</h2>

            <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
              {cart.map((item) => (
                <div key={item.product_id} className="flex items-center justify-between text-xs gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-[color:var(--color-text)] truncate">{item.name}</p>
                    <p className="text-[#8888aa]">Qty: {item.quantity} × ${item.price.toFixed(2)}</p>
                  </div>
                  <span className="font-semibold text-[color:var(--color-text)]">${(item.price * item.quantity).toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="border-t border-white/5 pt-3 space-y-2 text-xs text-[#8888aa]">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span className="text-[color:var(--color-text)] font-medium">${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Shipping</span>
                <span className="text-[color:var(--color-text)] font-medium">
                  {shipping === 0 ? "FREE" : `$${shipping.toFixed(2)}`}
                </span>
              </div>
              <div className="border-t border-white/5 pt-2 flex justify-between items-center text-sm font-bold text-[color:var(--color-text)]">
                <span>Total Amount</span>
                <span className="text-lg text-primary-300">${total.toFixed(2)}</span>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-sm transition-colors shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2"
            >
              {submitting ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <CheckCircle2 size={18} /> Place Order (${total.toFixed(2)})
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
