import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { User } from "../types";
import { ApiError, fetchMe } from "../api/client";

const TOKEN_KEY = "yt_recall_token";

export const AUTH_DISABLED = import.meta.env.VITE_AUTH_DISABLED === "true";
const DEV_TOKEN = "dev";

const NOT_ALLOWED_MESSAGE =
  "🔒 Sorry, your email has not been added to the allowlist. Email zara.tekmen@gmail.com if you want to be added!";

interface AuthState {
  token: string | null;
  user: User | null;
  loading: boolean;
  authError: string | null;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    AUTH_DISABLED ? DEV_TOKEN : localStorage.getItem(TOKEN_KEY),
  );
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(!!token);
  const [authError, setAuthError] = useState<string | null>(null);

  const logout = useCallback(() => {
    if (AUTH_DISABLED) return;
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const login = useCallback((newToken: string) => {
    setAuthError(null);
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchMe(token)
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch((err) => {
        if (cancelled) return;
        // A 403 means the account isn't on the allowlist; show a clear message
        // instead of silently bouncing the user back to a plain login screen.
        if (err instanceof ApiError && err.status === 403) {
          setAuthError(NOT_ALLOWED_MESSAGE);
        }
        logout();
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, logout]);

  const value = useMemo(
    () => ({ token, user, loading, authError, login, logout }),
    [token, user, loading, authError, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
