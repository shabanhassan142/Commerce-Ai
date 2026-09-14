// src/services/products.service.ts
// Product and category API calls

import api from "./api";
import type { Category, PaginatedProducts, Product } from "../types";

export interface ProductFilters {
  page?: number;
  per_page?: number;
  category_slug?: string;
  search?: string;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
}

const productsService = {
  async list(filters: ProductFilters = {}): Promise<PaginatedProducts> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    if (filters.category_slug) params.set("category_slug", filters.category_slug);
    if (filters.search) params.set("search", filters.search);
    if (filters.min_price != null) params.set("min_price", String(filters.min_price));
    if (filters.max_price != null) params.set("max_price", String(filters.max_price));
    if (filters.in_stock != null) params.set("in_stock", String(filters.in_stock));

    const { data } = await api.get<PaginatedProducts>(
      `/api/v1/products?${params.toString()}`
    );
    return data;
  },

  async getById(id: string): Promise<Product> {
    const { data } = await api.get<Product>(`/api/v1/products/${id}`);
    return data;
  },

  async getCategories(): Promise<Category[]> {
    const { data } = await api.get<Category[]>("/api/v1/products/categories");
    return data;
  },
};

export default productsService;
