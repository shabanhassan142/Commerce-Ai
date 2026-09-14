// src/services/orders.service.ts
// Order API calls

import api from "./api";
import type { Order, PaginatedOrders } from "../types";

export interface OrderFilters {
  page?: number;
  per_page?: number;
  status?: string;
}

const ordersService = {
  async list(filters: OrderFilters = {}): Promise<PaginatedOrders> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    if (filters.status) params.set("status", filters.status);

    const { data } = await api.get<PaginatedOrders>(
      `/api/v1/orders?${params.toString()}`
    );
    return data;
  },

  async getById(id: string): Promise<Order> {
    const { data } = await api.get<Order>(`/api/v1/orders/${id}`);
    return data;
  },
};

export default ordersService;
