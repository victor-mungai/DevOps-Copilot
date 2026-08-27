import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

// Authentication layer. There is no auth backend yet, so this is a temporary
// dev implementation (explicitly accepted by the sprint spec): users and the
// session live in localStorage. The shape mirrors a real token-based flow
// (access + refresh tokens) so swapping in a backend later is a drop-in.

export interface AuthUser {
  id: string;
  name: string;
  email: string;
}

interface Session {
  user: AuthUser;
  accessToken: string;
  refreshToken: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const USERS_KEY = 'devops-copilot.users';
const SESSION_KEY = 'devops-copilot.session';

interface StoredUser extends AuthUser {
  password: string;
}

function loadUsers(): StoredUser[] {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveUsers(users: StoredUser[]) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

// Fake tokens — opaque strings that look like JWTs for dev realism.
function mintTokens(user: AuthUser): { accessToken: string; refreshToken: string } {
  const stamp = Date.now();
  const encode = (kind: string) => btoa(`${kind}.${user.id}.${stamp}`).replace(/=/g, '');
  return { accessToken: encode('access'), refreshToken: encode('refresh') };
}

function uid(): string {
  return 'usr_' + Math.random().toString(36).slice(2, 10);
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadSession);

  useEffect(() => {
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else localStorage.removeItem(SESSION_KEY);
  }, [session]);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const normalized = email.trim().toLowerCase();
    if (!name.trim()) throw new Error('Name is required.');
    if (!normalized) throw new Error('Email is required.');
    if (password.length < 6) throw new Error('Password must be at least 6 characters.');

    const users = loadUsers();
    if (users.some((u) => u.email === normalized)) {
      throw new Error('An account with this email already exists.');
    }
    const user: StoredUser = { id: uid(), name: name.trim(), email: normalized, password };
    saveUsers([...users, user]);
    const { accessToken, refreshToken } = mintTokens(user);
    setSession({ user: { id: user.id, name: user.name, email: user.email }, accessToken, refreshToken });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const normalized = email.trim().toLowerCase();
    const users = loadUsers();
    const found = users.find((u) => u.email === normalized);
    if (!found || found.password !== password) {
      throw new Error('Invalid email or password.');
    }
    const { accessToken, refreshToken } = mintTokens(found);
    setSession({ user: { id: found.id, name: found.name, email: found.email }, accessToken, refreshToken });
  }, []);

  const logout = useCallback(() => setSession(null), []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      accessToken: session?.accessToken ?? null,
      isAuthenticated: Boolean(session),
      login,
      register,
      logout,
    }),
    [session, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
