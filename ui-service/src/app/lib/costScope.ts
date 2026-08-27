import { apiFetch } from './api';

export function scopedTenantIds(tenantId: string, isAllAccounts: boolean, workspaces: { tenantId: string }[]): string[] {
  return isAllAccounts ? workspaces.map((workspace) => workspace.tenantId).filter(Boolean) : [tenantId];
}

export async function fetchForScope<T>(tenantIds: string[], path: string, fallback: T): Promise<T[]> {
  const results = await Promise.allSettled(tenantIds.map((id) => apiFetch<T>(path.replace('{tenant_id}', id), { tenantId: id })));
  return results.filter((result): result is PromiseFulfilledResult<T> => result.status === 'fulfilled').map((result) => result.value);
}

function number(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

export function mergeSummaries(summaries: any[]): any | null {
  if (!summaries.length) return null;
  const first = summaries[0];
  const merged = { ...first };
  for (const key of ['total', 'total_cost', 'gross', 'credits', 'refunds', 'discounts', 'net', 'mtd_spend', 'previous_period', 'previous_period_net', 'previous_equivalent_period_spend', 'previous_full_month_spend']) {
    merged[key] = summaries.reduce((total, item) => total + number(item[key]), 0);
  }
  merged.change_percent = merged.previous_period > 0 ? ((merged.net - merged.previous_period) / Math.abs(merged.previous_period)) * 100 : null;
  merged.projected_monthly = summaries.every((item) => item.projected_monthly == null) ? null : summaries.reduce((total, item) => total + number(item.projected_monthly), 0);
  merged.forecast = merged.projected_monthly;
  merged.tenant_id = 'scoped-connected-workspaces';
  return merged;
}

export function mergeBreakdown(payloads: any[], collectionKey?: string): any[] {
  const rows = payloads.flatMap((payload) => collectionKey && !Array.isArray(payload) ? (payload[collectionKey] || []) : (Array.isArray(payload) ? payload : []));
  const grouped = new Map<string, any>();
  for (const row of rows) {
    const key = String(row.service ?? row.region ?? row.aws_account_id ?? row.account_name ?? row.name ?? '');
    if (!key) continue;
    const current = grouped.get(key) || { ...row, gross: 0, credits: 0, net: 0, cost: 0 };
    current.gross += number(row.gross);
    current.credits += number(row.credits);
    current.net += number(row.net ?? row.cost);
    current.cost = current.net;
    grouped.set(key, current);
  }
  const result = [...grouped.values()].sort((a, b) => b.net - a.net);
  const total = result.reduce((sum, row) => sum + row.net, 0);
  return result.map((row) => ({ ...row, percentage: total ? Number(((row.net / total) * 100).toFixed(2)) : 0 }));
}

export function mergeTrends(payloads: any[]): any[] {
  const grouped = new Map<string, any>();
  for (const row of payloads.flatMap((payload) => Array.isArray(payload) ? payload : [])) {
    const current = grouped.get(row.date) || { ...row, cost: 0, gross: 0, credits: 0, net: 0 };
    current.cost += number(row.cost ?? row.net);
    current.gross += number(row.gross);
    current.credits += number(row.credits);
    current.net += number(row.net ?? row.cost);
    grouped.set(row.date, current);
  }
  return [...grouped.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
}
