// src/pages/AdminProductDetail.tsx
// Detailed product admin view displaying stock, gallery, specs, and recent orders containing the product

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, DollarSign, Package, ShoppingBag, Star, Tag } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { stagger, staggerItem } from "../animations/variants";
import { ErrorState } from "../components/ui/ErrorState";
import { SkeletonCard } from "../components/ui/Skeleton";
import adminService from "../services/admin.service";
import type { AdminProductDetail } from "../types";

export default function AdminProductDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: product, isLoading, isError, refetch } = useQuery<AdminProductDetail>({
    queryKey: ["admin-product-detail", id],
    queryFn: () => adminService.getProductDetail(id!),
    enabled: !!id,
  });

  if (isError) return <ErrorState message="Could not load product details." onRetry={() => refetch()} />;
  if (isLoading) return <div className="p-6 space-y-4"><SkeletonCard /><SkeletonCard /></div>;
  if (!product) return <ErrorState message="Product not found." />;

  return (
    <motion.div variants={stagger} initial="hidden" animate="visible" className="space-y-6">
      {/* Back button */}
      <motion.div variants={staggerItem}>
        <button
          onClick={() => navigate("/admin/products")}
          className="inline-flex items-center gap-2 text-xs text-[#8888aa] hover:text-[color:var(--color-text)] transition-colors mb-2"
        >
          <ArrowLeft size={14} /> Back to Catalog & Inventory
        </button>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center overflow-hidden">
              {product.images.length > 0 ? (
                <img src={product.images[0].image_url} alt={product.name} className="w-full h-full object-cover" />
              ) : (
                <Package size={24} className="text-sky-400" />
              )}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[color:var(--color-text)] flex items-center gap-2">
                {product.name}
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase ${
                    product.stock === 0
                      ? "bg-red-500/20 text-red-400 border border-red-500/30"
                      : product.stock <= 5
                      ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  }`}
                >
                  {product.stock === 0 ? "Out of Stock" : `${product.stock} Units Available`}
                </span>
              </h1>
              <p className="text-xs text-[#8888aa] flex items-center gap-3 mt-1">
                <span>SKU: <strong className="text-white font-mono">{product.sku}</strong></span>
                {product.brand && <span>Brand: <strong className="text-white">{product.brand}</strong></span>}
                {product.category_name && <span>Category: <strong className="text-white">{product.category_name}</strong></span>}
                <span className="flex items-center gap-1 text-amber-400"><Star size={12} fill="currentColor" /> {product.rating} ({product.review_count} reviews)</span>
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <motion.div variants={staggerItem} className="card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-primary-500/10 text-primary-400 border border-primary-500/20 flex items-center justify-center">
            <Tag size={20} />
          </div>
          <div>
            <p className="text-xs text-[#8888aa]">Unit Selling Price</p>
            <p className="text-xl font-bold text-primary-300">PKR {Number(product.price).toLocaleString()}</p>
          </div>
        </motion.div>

        <motion.div variants={staggerItem} className="card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
            <ShoppingBag size={20} />
          </div>
          <div>
            <p className="text-xs text-[#8888aa]">Total Units Sold</p>
            <p className="text-xl font-bold text-[color:var(--color-text)]">{product.units_sold} units</p>
          </div>
        </motion.div>

        <motion.div variants={staggerItem} className="card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
            <DollarSign size={20} />
          </div>
          <div>
            <p className="text-xs text-[#8888aa]">Generated Revenue</p>
            <p className="text-xl font-bold text-emerald-400">PKR {Number(product.total_revenue).toLocaleString()}</p>
          </div>
        </motion.div>
      </div>

      {/* Product Image Gallery & Recent Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gallery */}
        <motion.div variants={staggerItem} className="card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
            <Package size={16} className="text-sky-400" /> Image Gallery ({product.images.length})
          </h2>
          {product.images.length === 0 ? (
            <p className="text-xs text-[#8888aa] py-6 text-center">No additional images uploaded.</p>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              {product.images.map((img) => (
                <div key={img.id} className="aspect-square rounded-xl overflow-hidden bg-white/5 border border-white/10 relative">
                  <img src={img.image_url} alt={img.alt_text || product.name} className="w-full h-full object-cover" />
                  {img.is_primary && (
                    <span className="absolute top-1 left-1 bg-primary-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded">
                      Primary
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Recent Orders containing product */}
        <motion.div variants={staggerItem} className="card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] flex items-center gap-2">
            <ShoppingBag size={16} className="text-primary-400" /> Recent Customer Orders
          </h2>
          {product.recent_orders.length === 0 ? (
            <p className="text-xs text-[#8888aa] py-6 text-center">No customer orders recorded for this product yet.</p>
          ) : (
            <div className="divide-y divide-white/5 text-xs">
              {product.recent_orders.map((o, i) => (
                <div
                  key={i}
                  onClick={() => navigate(`/admin/orders/${o.order_id}`)}
                  className="py-3 flex items-center justify-between hover:bg-white/5 px-2 rounded-lg cursor-pointer transition-colors"
                >
                  <div>
                    <p className="font-semibold text-primary-300">{o.order_number}</p>
                    <p className="text-[#8888aa] text-[11px]">{o.customer_name} · Qty: {o.quantity}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-[color:var(--color-text)]">PKR {Number(o.total_price).toLocaleString()}</p>
                    <p className="text-[10px] text-[#8888aa]">{new Date(o.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Specifications */}
      {product.specifications && Object.keys(product.specifications).length > 0 && (
        <motion.div variants={staggerItem} className="card p-5">
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] mb-3">Product Specifications</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
            {Object.entries(product.specifications).map(([key, value]) => (
              <div key={key} className="p-2.5 rounded-lg bg-white/5 border border-white/10">
                <span className="text-[#8888aa] block text-[10px] uppercase font-semibold">{key.replace(/_/g, " ")}</span>
                <span className="text-[color:var(--color-text)] font-medium">{String(value)}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
