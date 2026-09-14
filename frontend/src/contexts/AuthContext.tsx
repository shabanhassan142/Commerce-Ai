// src/contexts/AuthContext.tsx
// Global authentication state management

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import authService from "../services/auth.service";
import type { LoginPayload, RegisterPayload, User } from "../services/auth.service";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // ── Bootstrap — check if user is already logged in ─────────────────────────
  useEffect(() => {
    const init = async () => {
      if (!authService.isAuthenticated()) {
        setState({ user: null, isAuthenticated: false, isLoading: false });
        return;
      }

      try {
        const response = await authService.getMe();
        setState({
          user: response.data,
          isAuthenticated: true,
          isLoading: false,
        });
      } catch {
        authService.clearTokens();
        setState({ user: null, isAuthenticated: false, isLoading: false });
      }
    };

    init();
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const response = await authService.login(payload);
    if (!response?.data?.tokens) {
      throw new Error("Server returned an unexpected response. Please try again.");
    }
    authService.saveTokens(response.data.tokens);
    setState({
      user: response.data.user,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const response = await authService.register(payload);
    if (!response?.data?.tokens) {
      throw new Error("Server returned an unexpected response. Please try again.");
    }
    authService.saveTokens(response.data.tokens);
    setState({
      user: response.data.user,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setState({ user: null, isAuthenticated: false, isLoading: false });
    }
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
