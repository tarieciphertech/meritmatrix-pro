// Authentication context: login, logout, current user, and session bootstrap.
// Tokens live in localStorage (see lib/api.ts); the current user is fetched
// from GET /api/v1/auth/me on app start when tokens are present.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { api, apiRequest, ApiError, clearTokens, getStoredTokens, storeTokens } from './api';
import type { TokenResponse, UserResponse } from '../types';

interface AuthContextValue {
  user: UserResponse | null;
  initializing: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (roleName: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      const tokens = getStoredTokens();
      if (!tokens) {
        setInitializing(false);
        return;
      }
      try {
        const me = await api.get<UserResponse>('/api/v1/auth/me');
        if (!cancelled) setUser(me);
      } catch {
        clearTokens();
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setInitializing(false);
      }
    }
    void bootstrap();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (identifier: string, password: string) => {
    const tokens = await apiRequest<TokenResponse>(
      '/api/v1/auth/login',
      { method: 'POST', body: { identifier, password }, auth: false },
    );
    storeTokens(tokens);
    const me = await api.get<UserResponse>('/api/v1/auth/me');
    setUser(me);
  }, []);

  const logout = useCallback(async () => {
    const tokens = getStoredTokens();
    if (tokens) {
      try {
        await apiRequest<void>('/api/v1/auth/logout', {
          method: 'POST',
          body: { refresh_token: tokens.refresh_token },
        });
      } catch (err) {
        if (err instanceof ApiError && err.status !== 401) {
          console.warn('Logout revocation failed:', err.message);
        }
      }
    }
    clearTokens();
    setUser(null);
  }, []);

  const hasRole = useCallback(
    (roleName: string) => (user?.roles ?? []).some((r) => r.name === roleName),
    [user],
  );

  const value = useMemo(
    () => ({ user, initializing, login, logout, hasRole }),
    [user, initializing, login, logout, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}