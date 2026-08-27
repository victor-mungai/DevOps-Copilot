import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from './auth';

export interface Workspace {
  tenantId: string;
  tenantName: string;
  accountId: string;
  region: string;
}

export const DEFAULT_REGION = '';

export const AWS_REGIONS = [
  'us-east-1',
  'us-east-2',
  'us-west-1',
  'us-west-2',
  'eu-west-1',
  'eu-west-2',
  'eu-central-1',
  'ap-south-1',
  'ap-southeast-1',
  'ap-southeast-2',
  'ap-northeast-1',
  'sa-east-1',
];

export type TimePeriodKey = 'today' | '7d' | '30d' | '90d' | 'mtd' | 'prev_month' | 'custom';

export interface TimePeriodOption {
  key: TimePeriodKey;
  label: string;
}

export const TIME_PERIOD_OPTIONS: TimePeriodOption[] = [
  { key: 'mtd', label: 'Month to date' },
  { key: 'today', label: 'Today' },
  { key: '7d', label: '7 days' },
  { key: '30d', label: '30 days' },
  { key: '90d', label: '90 days' },
  { key: 'prev_month', label: 'Previous month' },
  { key: 'custom', label: 'Custom range' },
];

interface PersistShape {
  workspaces: Workspace[];
  activeId: string;
}

interface TenantContextValue {
  tenantId: string;
  tenantName: string;
  accountId: string;
  region: string;
  isConnected: boolean;
  isAllAccounts: boolean;

  workspaces: Workspace[];
  activeId: string;
  switchWorkspace: (tenantId: string) => void;

  timePeriod: TimePeriodKey;
  setTimePeriod: (p: TimePeriodKey) => void;
  customRange: { start: string; end: string };
  setCustomRange: (range: { start: string; end: string }) => void;

  periodLabel: string;
  scopeLabel: string;

  setTenant: (next: Partial<Workspace>) => void;
  setRegion: (region: string) => void;
  clearTenant: () => void;
}

const STORAGE_KEY = 'devops-copilot.workspaces';
const EMPTY: PersistShape = { workspaces: [], activeId: '' };

function storageKey(userId: string): string {
  return `${STORAGE_KEY}.${userId}`;
}

function loadInitial(userId: string): PersistShape {
  if (!userId) return EMPTY;
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Partial<PersistShape>;
    return {
      workspaces: Array.isArray(parsed.workspaces) ? parsed.workspaces : [],
      activeId: parsed.activeId ?? '',
    };
  } catch {
    return EMPTY;
  }
}

const TenantContext = createContext<TenantContextValue | null>(null);

export function TenantProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const userId = user?.id ?? '';
  const [state, setState] = useState<PersistShape>(() => loadInitial(userId));
  const [loadedUserId, setLoadedUserId] = useState(userId);
  const [timePeriod, setTimePeriod] = useState<TimePeriodKey>('mtd');
  const [customRange, setCustomRange] = useState<{ start: string; end: string }>({
    start: new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  const setTenant = useCallback((next: Partial<Workspace>) => {
    setState((prev) => {
      const targetId = (next.tenantId ?? prev.activeId ?? '').trim();
      if (!targetId) return prev;
      const idx = prev.workspaces.findIndex((w) => w.tenantId === targetId);
      const base: Workspace =
        idx >= 0
          ? prev.workspaces[idx]
          : { tenantId: targetId, tenantName: '', accountId: '', region: DEFAULT_REGION };
      const merged: Workspace = { ...base, ...next, tenantId: targetId };
      const workspaces =
        idx >= 0 ? prev.workspaces.map((w, i) => (i === idx ? merged : w)) : [...prev.workspaces, merged];
      return { workspaces, activeId: targetId };
    });
  }, []);

  useEffect(() => {
    setLoadedUserId(userId);
    setState(loadInitial(userId));
  }, [userId]);

  useEffect(() => {
    if (loadedUserId !== userId || !userId) return;
    try {
      if (state.workspaces.length > 0) {
        localStorage.setItem(storageKey(userId), JSON.stringify(state));
      } else {
        localStorage.removeItem(storageKey(userId));
      }
    } catch {}
  }, [state, loadedUserId, userId]);

  const switchWorkspace = useCallback((id: string) => {
    setState((prev) => ({ ...prev, activeId: id }));
  }, []);

  const setRegion = useCallback((region: string) => setTenant({ region }), [setTenant]);
  const clearTenant = useCallback(() => setState(EMPTY), []);

  const value = useMemo<TenantContextValue>(() => {
    const scopedState = loadedUserId === userId ? state : EMPTY;
    const hasWorkspaces = scopedState.workspaces.length > 0;
    const isAll = hasWorkspaces && (scopedState.activeId === 'all' || !scopedState.activeId);
    const active =
      scopedState.workspaces.find((w) => w.tenantId === scopedState.activeId) ??
      scopedState.workspaces[0] ??
      ({ tenantId: 'all', tenantName: 'All Accounts', accountId: 'All Accounts', region: '' } as Workspace);

    const activeTenantId = !hasWorkspaces ? '' : isAll ? 'all' : active.tenantId;
    const activeTenantName = !hasWorkspaces ? 'No workspace' : isAll ? 'All Accounts' : active.tenantName || 'Workspace';
    const activeAccountId = !hasWorkspaces ? '' : isAll ? 'All Accounts' : active.accountId || '';

    const periodLabel = computePeriodLabel(timePeriod, customRange);
    const scopeLabel = `${periodLabel} | ${activeTenantName}`;

    return {
      tenantId: activeTenantId,
      tenantName: activeTenantName,
      accountId: activeAccountId,
      region: active.region || '',
      isConnected: hasWorkspaces,
      isAllAccounts: isAll,

      workspaces: scopedState.workspaces,
      activeId: scopedState.activeId,
      switchWorkspace,

      timePeriod,
      setTimePeriod,
      customRange,
      setCustomRange,

      periodLabel,
      scopeLabel,

      setTenant,
      setRegion,
      clearTenant,
    };
  }, [state, loadedUserId, userId, timePeriod, customRange, switchWorkspace, setTenant, setRegion, clearTenant]);

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function periodQuery(period: TimePeriodKey, custom: { start: string; end: string }): string {
  const now = new Date();
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  let start = new Date(end);
  if (period === 'custom') {
    if (custom.start) start = new Date(`${custom.start}T00:00:00Z`);
    if (custom.end) end.setTime(new Date(`${custom.end}T00:00:00Z`).getTime());
  } else if (period === 'mtd') {
    start = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), 1));
  } else if (period === 'prev_month') {
    start = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - 1, 1));
    end.setTime(new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), 0)).getTime());
  } else {
    const days = period === 'today' ? 0 : period === '7d' ? 6 : period === '90d' ? 89 : 29;
    start.setUTCDate(start.getUTCDate() - days);
  }
  const iso = (value: Date) => value.toISOString().slice(0, 10);
  return `start_date=${iso(start)}&end_date=${iso(end)}`;
}

export function useTenant(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error('useTenant must be used within a TenantProvider');
  return ctx;
}

function computePeriodLabel(period: TimePeriodKey, custom: { start: string; end: string }): string {
  const now = new Date();
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const curMonth = months[now.getUTCMonth()];
  const curDay = now.getUTCDate();
  const curYear = now.getUTCFullYear();

  if (period === 'mtd') return `${curMonth} 1 – ${curMonth} ${curDay}, ${curYear}`;
  if (period === 'today') return `${curMonth} ${curDay}, ${curYear}`;
  if (period === '7d') return `Last 7 Days (${curMonth} ${Math.max(1, curDay - 7)}–${curDay})`;
  if (period === '30d') return `Last 30 Days`;
  if (period === '90d') return `Last 90 Days`;
  if (period === 'prev_month') {
    const prevM = months[(now.getUTCMonth() + 11) % 12];
    return `${prevM} ${curYear}`;
  }
  if (period === 'custom' && custom.start && custom.end) {
    return `${custom.start} to ${custom.end}`;
  }
  return `${curMonth} ${curYear}`;
}
