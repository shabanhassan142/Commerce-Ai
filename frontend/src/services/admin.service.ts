// src/services/admin.service.ts
// Data-driven Admin Console API service calls

import api from "./api";
import type {
  AdminAnalyticsData,
  AdminDashboardData,
  AdminOrderDetail,
  AdminProductDetail,
  AdminUserDetail,
  PaginatedAdminOrders,
  PaginatedAdminProducts,
  PaginatedAdminUsers,
} from "../types";

export interface AdminUserFilters {
  page?: number;
  per_page?: number;
  search?: string;
  role?: string;
  status?: string;
}

export interface AdminProductFilters {
  page?: number;
  per_page?: number;
  search?: string;
  category_slug?: string;
  stock_status?: string;
}

export interface AdminOrderFilters {
  page?: number;
  per_page?: number;
  search?: string;
  status?: string;
}

const adminService = {
  // ── Dashboard Overview ──────────────────────────────────────────────────────
  async getDashboardData(): Promise<AdminDashboardData> {
    const { data } = await api.get<AdminDashboardData>("/api/v1/admin/dashboard");
    return data;
  },

  // ── User Management ────────────────────────────────────────────────────────
  async getUsers(filters: AdminUserFilters = {}): Promise<PaginatedAdminUsers> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    if (filters.search) params.set("search", filters.search);
    if (filters.role) params.set("role", filters.role);
    if (filters.status) params.set("status", filters.status);

    const { data } = await api.get<PaginatedAdminUsers>(`/api/v1/admin/users?${params.toString()}`);
    return data;
  },

  async getUserDetail(userId: string): Promise<AdminUserDetail> {
    const { data } = await api.get<AdminUserDetail>(`/api/v1/admin/users/${userId}`);
    return data;
  },

  // ── Product Catalog Management ─────────────────────────────────────────────
  async getProducts(filters: AdminProductFilters = {}): Promise<PaginatedAdminProducts> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    if (filters.search) params.set("search", filters.search);
    if (filters.category_slug) params.set("category_slug", filters.category_slug);
    if (filters.stock_status) params.set("stock_status", filters.stock_status);

    const { data } = await api.get<PaginatedAdminProducts>(`/api/v1/admin/products?${params.toString()}`);
    return data;
  },

  async getProductDetail(productId: string): Promise<AdminProductDetail> {
    const { data } = await api.get<AdminProductDetail>(`/api/v1/admin/products/${productId}`);
    return data;
  },

  // ── Order Management ───────────────────────────────────────────────────────
  async getOrders(filters: AdminOrderFilters = {}): Promise<PaginatedAdminOrders> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    if (filters.search) params.set("search", filters.search);
    if (filters.status) params.set("status", filters.status);

    const { data } = await api.get<PaginatedAdminOrders>(`/api/v1/admin/orders?${params.toString()}`);
    return data;
  },

  async getOrderDetail(orderId: string): Promise<AdminOrderDetail> {
    const { data } = await api.get<AdminOrderDetail>(`/api/v1/admin/orders/${orderId}`);
    return data;
  },

  async updateOrderStatus(orderId: string, status: string): Promise<void> {
    await api.patch(`/api/v1/admin/orders/${orderId}/status`, { status });
  },

  // ── Real-Time Analytics ────────────────────────────────────────────────────
  async getAnalytics(): Promise<AdminAnalyticsData> {
    const { data } = await api.get<AdminAnalyticsData>("/api/v1/admin/analytics");
    return data;
  },
};

export default adminService;
