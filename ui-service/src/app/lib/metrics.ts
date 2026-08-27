import { apiFetch } from './api';

// Frontend client for the gateway's tenant-scoped Prometheus proxy.

export interface MetricPoint {
  t: number; // epoch ms
  value: number;
}

interface QueryResponse {
  metric: string;
  metric_name: string;
  resource: string | null;
  result: Array<{ metric: Record<string, string>; values: [number, string][] }>;
}

export type MetricKind = 'cpu' | 'memory' | 'network' | 'disk';

export async function fetchMetricRange(
  tenantId: string,
  metric: MetricKind,
  resource: string,
  minutes: number,
  step: number,
  region?: string
): Promise<MetricPoint[]> {
  const params = new URLSearchParams({
    metric,
    resource,
    minutes: String(minutes),
    step: String(step),
  });
  if (region) params.set('region', region);
  const res = await apiFetch<QueryResponse>(`/v1/metrics/query?${params.toString()}`, { tenantId });
  // Single-resource query → at most one series; flatten its values.
  const series = res.result[0]?.values ?? [];
  return series.map(([ts, val]) => ({ t: ts * 1000, value: Number(val) }));
}
