"use client";

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "./api";
import { UserPublic, TokenResponse } from "./types";

interface AuthContextValue {
  user: UserPublic | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.get<UserPublic>("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const hasToken = typeof window !== "undefined" && window.localStorage.getItem("netmentor_token");
    if (hasToken) {
      refreshUser();
    } else {
      setLoading(false);
    }
  }, [refreshUser]);

  async function login(email: string, password: string) {
    const res = await api.post<TokenResponse>("/auth/login", { email, password });
    setToken(res.access_token);
    setUser(res.user);
    router.push("/dashboard");
  }

  async function register(email: string, password: string, displayName: string) {
    const res = await api.post<TokenResponse>("/auth/register", { email, password, display_name: displayName });
    setToken(res.access_token);
    setUser(res.user);
    router.push("/dashboard");
  }

  function logout() {
    setToken(null);
    setUser(null);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
