// src/pages/Products.tsx
// Product marketplace with search, filter, sort, pagination

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Filter,
  Package,
  Search,
  Star,
  X,
} from "lucide-react";
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Pagination } from "../components/ui/Pagination";
import { SkeletonProductCard } from "../components/ui/Skeleton";
import productsService from "../services/products.service";
import type { ProductListItem } from "../types";
import { useDebounce } from "../hooks/useDebounce";

// ── Product Card ───────────────────────────────────────────────────────────────
function ProductCard({ product }: { product: ProductListItem }) {
  const price = Number(product.price);
  const originalPrice = product.original_price ? Number(product.original_price) : null;
  const discount = product.discount_percent;
  const hasDiscount = discount > 0 && originalPrice !== null;

  // Pick primary image from gallery, fallback to legacy image_url
  const primaryImg = product.images?.find((i) => i.is_primary)?.image_url
    ?? product.images?.[0]?.image_url
    ?? product.image_url;
  const hoverImg = product.images?.[1]?.image_url ?? null;

  const [hovered, setHovered] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card card-hover overflow-hidden group flex flex-col"
    >
      {/* Image container */}
      <div
        className="relative h-48 bg-[#1a1a2e] overflow-hidden flex-shrink-0"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {primaryImg ? (
          <>
            <img
              src={primaryImg}
              alt={product.name}
              className={`w-full h-full object-cover absolute inset-0 transition-opacity duration-400 ${
                hovered && hoverImg ? "opacity-0" : "opacity-100"
              }`}
              loading="lazy"
            />
            {hoverImg && (
              <img
                src={hoverImg}
                alt={`${product.name} alternate view`}
                className={`w-full h-full object-cover absolute inset-0 transition-opacity duration-400 ${
                  hovered ? "opacity-100" : "opacity-0"
                }`}
                loading="lazy"
              />
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Package size={40} className="text-primary-400/30" />
          </div>
        )}

        {/* Discount badge */}
        {hasDiscount && (
          <span className="absolute top-2 left-2 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500 text-white shadow">
            -{Math.round(discount)}% OFF
          </span>
        )}

        {/* Image count dots */}
        {(product.images?.length ?? 0) > 1 && (
          <div className="absolute bottom-2 right-2 flex gap-1">
            {product.images.slice(0, 4).map((_, i) => (
              <span
                key={i}
                className={`w-1.5 h-1.5 rounded-full transition-colors ${
                  i === 0 && !hovered ? "bg-white" : i === 1 && hovered ? "bg-white" : "bg-white/40"
                }`}
              />
            ))}
          </div>
        )}

        {/* Out of stock overlay */}
        {product.stock === 0 && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
            <span className="text-xs font-semibold text-white bg-black/70 px-3 py-1 rounded-full">
              Out of Stock
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4 flex flex-col flex-1">
        {/* Category + Brand row */}
        <div className="flex items-center justify-between mb-1">
          {product.category && (
            <p className="text-[10px] font-semibold text-primary-400 uppercase tracking-wide">
              {product.category.icon} {product.category.name}
            </p>
          )}
          {product.brand && (
            <p className="text-[10px] text-[#6666aa] font-medium truncate ml-1">{product.brand}</p>
          )}
        </div>

        {/* Name */}
        <h3 className="text-sm font-semibold text-[color:var(--color-text)] leading-tight mb-2 line-clamp-2 group-hover:text-primary-300 transition-colors flex-1">
          {product.name}
        </h3>

        {/* Rating */}
        <div className="flex items-center gap-1 mb-2">
          <Star size={11} className="text-amber-400 fill-amber-400 flex-shrink-0" />
          <span className="text-xs text-[#8888aa]">
            {product.rating.toFixed(1)}{" "}
            <span className="text-[#666688]">({product.review_count.toLocaleString()})</span>
          </span>
        </div>

        {/* Price */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-lg font-bold text-[color:var(--color-text)]">
            ${price.toFixed(2)}
          </span>
          {hasDiscount && originalPrice && (
            <span className="text-xs text-[#8888aa] line-through">${originalPrice.toFixed(2)}</span>
          )}
        </div>

        {/* Stock */}
        <p className="text-[10px] mb-3">
          {product.stock > 10 ? (
            <span className="text-emerald-400">● In Stock</span>
          ) : product.stock > 0 ? (
            <span className="text-amber-400">● Low Stock — {product.stock} left</span>
          ) : (
            <span className="text-red-400">● Out of Stock</span>
          )}
        </p>

        <Link
          to={`/products/${product.id}`}
          className="mt-auto block text-center text-sm font-medium px-4 py-2 rounded-lg border border-primary-500/30 text-primary-400 hover:bg-primary-500/15 hover:border-primary-500/60 transition-all duration-200"
        >
          View Product
        </Link>
      </div>
    </motion.div>
  );
}

// ── Main Products Page ────────────────────────────────────────────────────────
export default function Products() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [categorySlug, setCategorySlug] = useState("");
  const [inStock, setInStock] = useState<boolean | undefined>();
  const [minPrice, setMinPrice] = useState<number | undefined>();
  const [maxPrice, setMaxPrice] = useState<number | undefined>();
  const [showFilters, setShowFilters] = useState(false);

  const debouncedSearch = useDebounce(search, 400);

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => productsService.getCategories(),
    staleTime: Infinity,
  });

  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["products", { page, search: debouncedSearch, categorySlug, inStock, minPrice, maxPrice }],
    queryFn: () =>
      productsService.list({
        page,
        per_page: 12,
        search: debouncedSearch || undefined,
        category_slug: categorySlug || undefined,
        in_stock: inStock,
        min_price: minPrice,
        max_price: maxPrice,
      }),
  });

  const clearFilters = useCallback(() => {
    setSearch("");
    setCategorySlug("");
    setInStock(undefined);
    setMinPrice(undefined);
    setMaxPrice(undefined);
    setPage(1);
  }, []);

  const hasFilters = search || categorySlug || inStock != null || minPrice != null || maxPrice != null;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--color-text)]">Products</h1>
          <p className="text-[#8888aa] text-sm mt-0.5">
            {data ? `${data.total.toLocaleString()} products available` : "Browse our marketplace"}
          </p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm border transition-colors ${
            showFilters ? "bg-primary-500/15 border-primary-500/30 text-primary-300" : "border-white/10 text-[#8888aa] hover:text-[color:var(--color-text)] hover:bg-white/5"
          }`}
        >
          <Filter size={15} />
          Filters
          {hasFilters && <span className="w-1.5 h-1.5 rounded-full bg-primary-400" />}
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8888aa]" />
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search products…"
          className="input-field pl-10 pr-10"
          aria-label="Search products"
        />
        {search && (
          <button onClick={() => setSearch("")} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#8888aa] hover:text-[color:var(--color-text)]">
            <X size={14} />
          </button>
        )}
      </div>

      {/* Filter panel */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="card p-4 space-y-4"
        >
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Category */}
            <div>
              <label className="label">Category</label>
              <select
                value={categorySlug}
                onChange={(e) => { setCategorySlug(e.target.value); setPage(1); }}
                className="input-field"
                aria-label="Category filter"
              >
                <option value="">All Categories</option>
                {categories?.map((c) => (
                  <option key={c.id} value={c.slug}>{c.icon} {c.name}</option>
                ))}
              </select>
            </div>

            {/* Price range */}
            <div>
              <label className="label">Min Price ($)</label>
              <input
                type="number"
                min={0}
                value={minPrice ?? ""}
                onChange={(e) => { setMinPrice(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
                placeholder="0"
                className="input-field"
                aria-label="Minimum price"
              />
            </div>
            <div>
              <label className="label">Max Price ($)</label>
              <input
                type="number"
                min={0}
                value={maxPrice ?? ""}
                onChange={(e) => { setMaxPrice(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
                placeholder="Any"
                className="input-field"
                aria-label="Maximum price"
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-[color:var(--color-text)]">
              <input
                type="checkbox"
                checked={inStock === true}
                onChange={(e) => { setInStock(e.target.checked ? true : undefined); setPage(1); }}
                className="rounded border-primary-500/30 accent-primary-500"
              />
              In stock only
            </label>
            {hasFilters && (
              <button onClick={clearFilters} className="text-xs text-[#8888aa] hover:text-red-400 flex items-center gap-1 transition-colors">
                <X size={12} /> Clear filters
              </button>
            )}
          </div>
        </motion.div>
      )}

      {/* Category tabs */}
      {categories && categories.length > 0 && !showFilters && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => { setCategorySlug(""); setPage(1); }}
            className={`flex-shrink-0 px-4 py-1.5 rounded-full text-xs font-medium transition-colors ${!categorySlug ? "bg-primary-600 text-white" : "bg-white/5 text-[#8888aa] hover:bg-white/10 hover:text-[color:var(--color-text)]"}`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => { setCategorySlug(cat.slug); setPage(1); }}
              className={`flex-shrink-0 px-4 py-1.5 rounded-full text-xs font-medium transition-colors ${categorySlug === cat.slug ? "bg-primary-600 text-white" : "bg-white/5 text-[#8888aa] hover:bg-white/10 hover:text-[color:var(--color-text)]"}`}
            >
              {cat.icon} {cat.name}
            </button>
          ))}
        </div>
      )}

      {/* Grid */}
      {isError ? (
        <ErrorState message="We couldn't load products." onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 12 }).map((_, i) => <SkeletonProductCard key={i} />)}
        </div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon={Package}
          title="No products found"
          description="Try adjusting your filters or search terms."
          action={{ label: "Clear filters", onClick: clearFilters }}
        />
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {data?.items.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
          {data && (
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              perPage={data.per_page}
              onPageChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}
