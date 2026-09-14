// src/pages/ProductDetail.tsx
// Full product detail page with image gallery, specifications, and AI integration

import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Bot,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Minus,
  Package,
  Plus,
  ShoppingCart,
  Star,
  Store,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import useAuth from "../hooks/useAuth";
import cartService from "../services/cart.service";
import productsService from "../services/products.service";
import type { Product, ProductImage } from "../types";

// ── Image Gallery ─────────────────────────────────────────────────────────────
function ImageGallery({ images, productName }: { images: ProductImage[]; productName: string }) {
  const [activeIdx, setActiveIdx] = useState(0);

  if (images.length === 0) {
    return (
      <div className="h-80 rounded-2xl bg-[#1a1a2e] flex items-center justify-center">
        <Package size={64} className="text-primary-400/20" />
      </div>
    );
  }

  const prev = () => setActiveIdx((i) => (i - 1 + images.length) % images.length);
  const next = () => setActiveIdx((i) => (i + 1) % images.length);

  return (
    <div className="space-y-3">
      {/* Main image */}
      <div className="relative h-80 sm:h-96 rounded-2xl overflow-hidden bg-[#1a1a2e] group">
        <AnimatePresence mode="wait">
          <motion.img
            key={activeIdx}
            src={images[activeIdx].image_url}
            alt={images[activeIdx].alt_text ?? productName}
            className="w-full h-full object-cover"
            initial={{ opacity: 0, scale: 1.03 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.25 }}
          />
        </AnimatePresence>

        {/* Nav arrows */}
        {images.length > 1 && (
          <>
            <button
              onClick={prev}
              className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
              aria-label="Previous image"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={next}
              className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
              aria-label="Next image"
            >
              <ChevronRight size={16} />
            </button>

            {/* Dot indicators */}
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
              {images.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveIdx(i)}
                  className={`w-1.5 h-1.5 rounded-full transition-all ${
                    i === activeIdx ? "bg-white w-4" : "bg-white/40"
                  }`}
                  aria-label={`View image ${i + 1}`}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {images.map((img, i) => (
            <button
              key={img.id}
              onClick={() => setActiveIdx(i)}
              className={`flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all ${
                i === activeIdx
                  ? "border-primary-500 opacity-100"
                  : "border-white/10 opacity-50 hover:opacity-80"
              }`}
              aria-label={`Thumbnail ${i + 1}`}
            >
              <img
                src={img.image_url}
                alt={img.alt_text ?? `${productName} view ${i + 1}`}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main ProductDetail ────────────────────────────────────────────────────────
export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: product, isLoading, isError, refetch } = useQuery({
    queryKey: ["product", id],
    queryFn: () => productsService.getById(id!),
    enabled: !!id,
  });

  const askAI = () => {
    if (product) {
      navigate(`/chat`, {
        state: {
          product_id: product.id,
          product_name: product.name,
          initialMessage: `Tell me about ${product.name}`,
        },
      });
    }
  };

  if (isError) return <ErrorState message="Product not found." onRetry={() => refetch()} type="notfound" />;

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm text-[#8888aa] hover:text-[color:var(--color-text)] transition-colors"
      >
        <ArrowLeft size={15} /> Back
      </button>

      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-3">
            <Skeleton className="h-80 rounded-2xl" />
            <div className="flex gap-2">
              {[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-16 rounded-lg" />)}
            </div>
          </div>
          <div className="space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-12 w-1/3" />
            <Skeleton className="h-24 w-full" />
          </div>
        </div>
      ) : product ? (
        <ProductContent product={product} onAskAI={askAI} />
      ) : null}
    </div>
  );
}

// ── Product Content (separated for clarity) ───────────────────────────────────
function ProductContent({ product, onAskAI }: { product: Product; onAskAI: () => void }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [quantity, setQuantity] = useState(1);

  const price = Number(product.price);
  const originalPrice = product.original_price ? Number(product.original_price) : null;
  const discount = product.discount_percent;
  const hasDiscount = discount > 0 && originalPrice !== null;
  const inStock = product.stock > 0;
  const lowStock = product.stock > 0 && product.stock <= 10;

  const handleAddToCart = () => {
    if (!user) {
      toast.error("Please log in to add items to your cart.");
      navigate("/login");
      return;
    }
    cartService.addToCart(user.id, product, quantity);
    toast.success(`Added ${quantity} × ${product.name} to cart!`, {
      action: {
        label: "View Cart",
        onClick: () => navigate("/cart"),
      },
    });
  };

  // Build images array — prefer the images gallery, fallback to legacy image_url
  const images: ProductImage[] = product.images?.length > 0
    ? product.images
    : product.image_url
    ? [{ id: "legacy", image_url: product.image_url, is_primary: true, sort_order: 0 }]
    : [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="grid grid-cols-1 lg:grid-cols-2 gap-8"
    >
      {/* ── LEFT: Image Gallery ── */}
      <ImageGallery images={images} productName={product.name} />

      {/* ── RIGHT: Info ── */}
      <div className="space-y-5">
        {/* Category breadcrumb */}
        {product.category && (
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
            {product.category.icon} {product.category.name}
          </p>
        )}

        {/* Title + brand */}
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)] leading-tight">
            {product.name}
          </h1>
          {product.brand && (
            <p className="text-sm text-[#8888aa] mt-1">by <span className="text-primary-300 font-medium">{product.brand}</span></p>
          )}
        </div>

        {/* Rating */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5">
            {[1, 2, 3, 4, 5].map((star) => (
              <Star
                key={star}
                size={14}
                className={
                  star <= Math.round(product.rating)
                    ? "text-amber-400 fill-amber-400"
                    : "text-[#444466] fill-[#444466]"
                }
              />
            ))}
          </div>
          <span className="text-sm text-[color:var(--color-text)] font-semibold">{product.rating.toFixed(1)}</span>
          <span className="text-sm text-[#8888aa]">({product.review_count.toLocaleString()} reviews)</span>
        </div>

        {/* Pricing */}
        <div className="card p-4 space-y-1.5">
          <div className="flex items-end gap-3">
            <span className="text-3xl font-bold text-[color:var(--color-text)]">${price.toFixed(2)}</span>
            {hasDiscount && originalPrice && (
              <>
                <span className="text-lg text-[#8888aa] line-through mb-0.5">${originalPrice.toFixed(2)}</span>
                <span className="px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 text-sm font-semibold border border-red-500/20 mb-0.5">
                  {Math.round(discount)}% OFF
                </span>
              </>
            )}
          </div>
          {hasDiscount && originalPrice && (
            <p className="text-xs text-emerald-400">
              You save ${(originalPrice - price).toFixed(2)}
            </p>
          )}
        </div>

        {/* Stock status */}
        <div className="flex items-center gap-2">
          {inStock ? (
            <>
              <CheckCircle size={16} className="text-emerald-400" />
              <span className="text-sm text-emerald-400 font-medium">
                {lowStock ? `Low Stock — Only ${product.stock} left!` : "In Stock"}
              </span>
            </>
          ) : (
            <>
              <XCircle size={16} className="text-red-400" />
              <span className="text-sm text-red-400 font-medium">Out of Stock</span>
            </>
          )}
          <span className="text-xs text-[#666688] ml-1">SKU: {product.sku}</span>
        </div>

        {/* Description */}
        <div>
          <h2 className="text-sm font-semibold text-[color:var(--color-text)] mb-1.5">Description</h2>
          <p className="text-sm text-[#8888aa] leading-relaxed">{product.description}</p>
        </div>

        {/* Quantity + Add to Cart controls */}
        {inStock ? (
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
            <div className="flex items-center justify-between border border-white/10 rounded-xl px-3 py-2 bg-white/5 w-full sm:w-36">
              <button
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                disabled={quantity <= 1}
                className="text-[#8888aa] hover:text-white disabled:opacity-30 p-1"
                aria-label="Decrease quantity"
              >
                <Minus size={16} />
              </button>
              <span className="font-semibold text-sm text-[color:var(--color-text)] px-3">{quantity}</span>
              <button
                onClick={() => setQuantity((q) => Math.min(product.stock, q + 1))}
                disabled={quantity >= product.stock}
                className="text-[#8888aa] hover:text-white disabled:opacity-30 p-1"
                aria-label="Increase quantity"
              >
                <Plus size={16} />
              </button>
            </div>

            <button
              onClick={handleAddToCart}
              className="flex-1 flex items-center justify-center gap-2.5 py-3 px-6 rounded-xl font-semibold text-sm
                bg-primary-600 hover:bg-primary-500 text-white transition-all duration-150 shadow-lg shadow-primary-500/20"
            >
              <ShoppingCart size={17} />
              Add to Cart
            </button>
          </div>
        ) : (
          <button
            disabled
            className="w-full py-3 px-6 rounded-xl font-semibold text-sm bg-white/5 border border-white/10 text-red-400 cursor-not-allowed text-center"
          >
            Out of Stock
          </button>
        )}

        {/* Ask AI button */}
        <button
          onClick={onAskAI}
          className="w-full flex items-center justify-center gap-2.5 py-3 px-6 rounded-xl font-semibold text-sm
            bg-gradient-to-r from-primary-600 to-accent-600 text-white
            hover:from-primary-500 hover:to-accent-500 transition-all duration-200
            shadow-lg shadow-primary-500/20 hover:shadow-primary-500/30 hover:scale-[1.01]"
        >
          <Bot size={17} />
          Ask AI about this product
        </button>

        {/* Seller info */}
        {product.seller && (
          <div className="flex items-center gap-3 p-3 rounded-xl border border-white/8 bg-white/3">
            <Store size={16} className="text-primary-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[color:var(--color-text)] truncate">
                {product.seller.name}
                {product.seller.is_verified && (
                  <span className="ml-1.5 text-[10px] text-emerald-400 font-semibold">✓ Verified</span>
                )}
              </p>
              <p className="text-xs text-[#8888aa]">
                {product.seller.city} · ⭐ {product.seller.rating.toFixed(1)}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── FULL WIDTH: Specifications ── */}
      {product.specifications && Object.keys(product.specifications).length > 0 && (
        <div className="lg:col-span-2">
          <div className="card p-5">
            <h2 className="text-base font-semibold text-[color:var(--color-text)] mb-4">Specifications</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(product.specifications).map(([key, value]) => (
                <div key={key} className="flex flex-col gap-0.5 p-3 rounded-lg bg-white/3 border border-white/6">
                  <span className="text-[10px] font-semibold text-primary-400 uppercase tracking-wider">{key}</span>
                  <span className="text-sm text-[color:var(--color-text)]">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
