/**
 * 認証状態を管理する Context / hook。
 */

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

import * as api from "../utils/api";

interface AuthState {
  user: api.MeResponse | null;
  loading: boolean;
  error: string | null;
  login: (email: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<api.MeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (email: string) => {
    setLoading(true);
    setError(null);
    try {
      const token = await api.login(email);
      api.setToken(token.access_token);
      const me = await api.fetchMe();
      setUser(me);
    } catch (e) {
      api.setToken(null);
      setError(
        e instanceof api.ApiClientError
          ? e.detail
          : "ログインに失敗しました。通信環境を確認してください。"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    api.setToken(null);
    setUser(null);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, login, logout }),
    [user, loading, error, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
