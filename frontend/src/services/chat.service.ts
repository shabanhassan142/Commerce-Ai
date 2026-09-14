// src/services/chat.service.ts
// AI chat API calls and local conversation history management

import api from "./api";
import type { ApiResponse, ChatConversation, ChatMessage } from "../types";

const HISTORY_KEY = "cf_conversations";
const MAX_STORED = 10;

export interface ChatApiRequest {
  message: string;
  conversation_id?: string;
  product_id?: string;
}

export interface ChatApiResponse {
  answer: string;
  conversation_id?: string;
  intent?: string;
  agent?: string;
  confidence?: number;
  citations?: Array<{
    source?: string;
    title?: string;
    content?: string;
    relevance?: number;
    score?: number;
  }>;
  escalated?: boolean;
  ticket_id?: string;
}

const chatService = {
  async sendMessage(payload: ChatApiRequest): Promise<ChatApiResponse> {
    const { data } = await api.post<ApiResponse<ChatApiResponse & { message?: string }>>(
      "/api/v1/chat",
      payload
    );
    const raw = data.data;
    return {
      ...raw,
      answer: raw.answer ?? raw.message ?? "No response received.",
    };
  },

  // ── Local conversation history (localStorage) ──────────────────────────────
  getConversations(): ChatConversation[] {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  saveConversation(conversation: ChatConversation): void {
    try {
      const all = chatService.getConversations();
      const idx = all.findIndex((c) => c.id === conversation.id);
      if (idx >= 0) {
        all[idx] = conversation;
      } else {
        all.unshift(conversation);
      }
      // keep only the most recent MAX_STORED
      localStorage.setItem(
        HISTORY_KEY,
        JSON.stringify(all.slice(0, MAX_STORED))
      );
    } catch {
      // silently fail on storage quota errors
    }
  },

  deleteConversation(id: string): void {
    try {
      const all = chatService.getConversations().filter((c) => c.id !== id);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(all));
    } catch {}
  },

  clearAll(): void {
    localStorage.removeItem(HISTORY_KEY);
  },

  newMessage(
    role: ChatMessage["role"],
    content: string,
    extras?: Partial<ChatMessage>
  ): ChatMessage {
    return {
      id: crypto.randomUUID(),
      role,
      content,
      timestamp: new Date().toISOString(),
      ...extras,
    };
  },

  generateTitle(firstMessage: string): string {
    return firstMessage.length > 50
      ? firstMessage.slice(0, 50) + "…"
      : firstMessage;
  },
};

export default chatService;
