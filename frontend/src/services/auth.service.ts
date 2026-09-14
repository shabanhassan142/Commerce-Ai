// src/services/auth.service.ts
// Auth API calls for register, login, refresh, me, logout

import api from "./api";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "customer" | "support" | "admin";
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  data: {
    user: User;
    tokens: Tokens;
  };
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  role?: "customer" | "support" | "admin";
}

export interface LoginPayload {
  email: string;
  password: string;
}

const authService = {
  async register(payload: RegisterPayload): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>("/api/v1/auth/register", payload);
    return data;
  },

  async login(payload: LoginPayload): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>("/api/v1/auth/login", payload);
    return data;
  },

  async getMe(): Promise<{ success: boolean; data: User }> {
    const { data } = await api.get("/api/v1/auth/me");
    return data;
  },

  async logout(): Promise<void> {
    await api.post("/api/v1/auth/logout");
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },

  saveTokens(tokens: Tokens): void {
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
  },

  clearTokens(): void {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },

  getAccessToken(): string | null {
    return localStorage.getItem("access_token");
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem("access_token");
  },
};

export default authService;
