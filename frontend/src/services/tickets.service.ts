// src/services/tickets.service.ts
// Support ticket API calls — both customer (/my/tickets) and agent (/tickets) routes

import api from "./api";
import type {
  ApiResponse,
  PaginatedTickets,
  TicketDetail,
  TicketNote,
  TicketReply,
} from "../types";

export interface TicketFilters {
  page?: number;
  per_page?: number;
  status?: string;
  priority?: string;
}

export interface CreateTicketPayload {
  subject: string;
  description: string;
  priority?: "low" | "medium" | "high" | "urgent";
  order_id?: string;
}

export interface ReplyPayload {
  content: string;
}

export interface AssignPayload {
  agent_id: string | null;
}

export interface StatusPayload {
  status: string;
}

export interface PriorityPayload {
  priority: string;
}

export interface NotePayload {
  content: string;
}

const ticketsService = {
  // ── Customer routes (/my/tickets) ──────────────────────────────────────────
  async listMine(filters: TicketFilters = {}): Promise<PaginatedTickets> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    if (filters.status) params.set("status", filters.status);
    const { data } = await api.get<ApiResponse<PaginatedTickets>>(
      `/api/v1/my/tickets?${params.toString()}`
    );
    return data.data;
  },

  async getMine(id: string): Promise<TicketDetail> {
    const { data } = await api.get<ApiResponse<TicketDetail>>(
      `/api/v1/my/tickets/${id}`
    );
    return data.data;
  },

  async replyMine(id: string, payload: ReplyPayload): Promise<TicketReply> {
    const { data } = await api.post<ApiResponse<TicketReply>>(
      `/api/v1/my/tickets/${id}/reply`,
      payload
    );
    return data.data;
  },

  // ── Agent/Admin routes (/tickets) ──────────────────────────────────────────
  async list(filters: TicketFilters = {}): Promise<PaginatedTickets> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    if (filters.status) params.set("status", filters.status);
    if (filters.priority) params.set("priority", filters.priority);
    const { data } = await api.get<ApiResponse<PaginatedTickets>>(
      `/api/v1/tickets?${params.toString()}`
    );
    return data.data;
  },

  async getById(id: string): Promise<TicketDetail> {
    const { data } = await api.get<ApiResponse<TicketDetail>>(
      `/api/v1/tickets/${id}`
    );
    return data.data;
  },

  async create(payload: CreateTicketPayload): Promise<TicketDetail> {
    const { data } = await api.post<ApiResponse<TicketDetail>>(
      "/api/v1/tickets",
      payload
    );
    return data.data;
  },

  async assign(id: string, payload: AssignPayload): Promise<TicketDetail> {
    const { data } = await api.patch<ApiResponse<TicketDetail>>(
      `/api/v1/tickets/${id}/assign`,
      payload
    );
    return data.data;
  },

  async updateStatus(id: string, payload: StatusPayload): Promise<TicketDetail> {
    const { data } = await api.patch<ApiResponse<TicketDetail>>(
      `/api/v1/tickets/${id}/status`,
      payload
    );
    return data.data;
  },

  async updatePriority(
    id: string,
    payload: PriorityPayload
  ): Promise<TicketDetail> {
    const { data } = await api.patch<ApiResponse<TicketDetail>>(
      `/api/v1/tickets/${id}/priority`,
      payload
    );
    return data.data;
  },

  async addNote(id: string, payload: NotePayload): Promise<TicketNote> {
    const { data } = await api.post<ApiResponse<TicketNote>>(
      `/api/v1/tickets/${id}/notes`,
      payload
    );
    return data.data;
  },

  async reply(id: string, payload: ReplyPayload): Promise<TicketReply> {
    const { data } = await api.post<ApiResponse<TicketReply>>(
      `/api/v1/tickets/${id}/reply`,
      payload
    );
    return data.data;
  },

  // ── Utility queues ─────────────────────────────────────────────────────────
  async listOpen(filters: TicketFilters = {}): Promise<PaginatedTickets> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    const { data } = await api.get<ApiResponse<PaginatedTickets>>(
      `/api/v1/tickets/open?${params.toString()}`
    );
    return data.data;
  },

  async listAssignedToMe(filters: TicketFilters = {}): Promise<PaginatedTickets> {
    const params = new URLSearchParams();
    if (filters.page) params.set("page", String(filters.page));
    if (filters.per_page) params.set("per_page", String(filters.per_page));
    const { data } = await api.get<ApiResponse<PaginatedTickets>>(
      `/api/v1/tickets/assigned/me?${params.toString()}`
    );
    return data.data;
  },
};

export default ticketsService;
