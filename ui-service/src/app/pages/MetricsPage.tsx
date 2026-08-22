import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  LineChart as RLineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Brush,
} from 'recharts';
import { LineChart, PlugZap, RefreshCw, Radio } from 'lucide-react';
import { errorMessage } from '../lib/api';
import { fetchEc2, fetchLambda, fetchRds } from '../lib/aws';
import { fetchMetricRange } from '../lib/metrics';
import type { MetricKind, MetricPoint } from '../lib/metrics';
import { useTenant } from '../lib/tenant';
import type { Ec2Row, LambdaRow, RdsRow } from '../lib/types';
import { EmptyState, ErrorBanner, Panel, Spinner } from '../components/dashboard/primitives';

const METRICS: { key: MetricKind; label: string; unit: string; color: string }[] = [
  { key: 'cpu', label: 'CPU Utilization', unit: '%', color: '#10b981' },
  { key: 'memory', label: 'Memory Utilization', unit: '%', color: '#38bdf8' },
  { key: 'network', label: 'Network Traffic', unit: 'B', color: '#a78bfa' },
  { key: 'disk', label: 'Disk Usage', unit: '%', color: '#f59e0b' },
];

const RANGES = [
  { label: '1h', minutes: 60, step: 60 },
  { label: '6h', minutes: 360, step: 120 },
  { label: '24h', minutes: 1440, step: 300 },
  { label: '7d', minutes: 10080, step: 1800 },
  { label: '30d', minutes: 43200, step: 7200 },
];

const POLL_MS = 15000;
const SYNC_ID = 'metrics-explorer'; // shared → synchronized crosshair across panels

type SeriesMap = Record<MetricKind, MetricPoint[]>;

interface GroupedResources {
  ec2: Ec2Row[];
  rds: RdsRow[];
  lambda: LambdaRow[];
}

export function MetricsPage() {
  const navigate = useNavigate();
  const { tenantId, region, isConnected } = useTenant();
  const [resources, setResources] = useState<GroupedResources>({ ec2: [], rds: [], lambda: [] });
  const [resource, setResource] = useState('');
  const [selected, setSelected] = useState<Set<MetricKind>>(new Set(['cpu', 'memory', 'network', 'disk']));
  const [rangeIdx, setRangeIdx] = useState(1);
  const [series, setSeries] = useState<SeriesMap>({ cpu: [], memory: [], network: [], disk: [] });
  const [loading, setLoading] = useState(false);
  const [live, setLive] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const range = RANGES[rangeIdx];

  // Resource picker from region-scoped EC2, RDS, and Lambda inventory
  useEffect(() => {
    if (!tenantId) return;
    Promise.allSettled([
      fetchEc2(tenantId, region),
      fetchRds(tenantId, region),
      fetchLambda(tenantId, region),
    ]).then(([ec2Res, rdsRes, lambdaRes]) => {
      const ec2 = ec2Res.status === 'fulfilled' ? ec2Res.value : [];
      const rds = rdsRes.status === 'fulfilled' ? rdsRes.value : [];
      const lambda = lambdaRes.status === 'fulfilled' ? lambdaRes.value : [];
      setResources({ ec2, rds, lambda });

      const allIds = [
        ...ec2.map((x) => x.resourceId),
        ...rds.map((x) => x.resourceId),
        ...lambda.map((x) => x.resourceId),
      ];

      setResource((prev) => (allIds.includes(prev) ? prev : allIds[0] ?? ''));
    });
  }, [tenantId, region]);

  const load = useCallback(
    async (showSpinner = true) => {
      if (!tenantId || !resource) return;
      if (showSpinner) setLoading(true);
      setError('');
      try {
        const kinds = Array.from(selected);
        const results = await Promise.all(
          kinds.map((k) => fetchMetricRange(tenantId, k, resource, range.minutes, range.step, region))
        );
        setSeries((prev) => {
          const next = { ...prev };
          kinds.forEach((k, i) => (next[k] = results[i]));
          return next;
        });
        setLastUpdated(Date.now());
      } catch (e) {
        setError(errorMessage(e));
      } finally {
        if (showSpinner) setLoading(false);
      }
    },
    [tenantId, resource, region, selected, range.minutes, range.step]
  );

  useEffect(() => {
    void load(true);
  }, [load]);

  // Live polling — every 15s, silent refresh
  const loadRef = useRef(load);
  loadRef.current = load;
  useEffect(() => {
    if (!live || !isConnected) return;
    const id = setInterval(() => void loadRef.current(false), POLL_MS);
    return () => clearInterval(id);
  }, [live, isConnected]);

  const handleResourceChange = (newResourceId: string) => {
    setSeries({ cpu: [], memory: [], network: [], disk: [] });
    setResource(newResourceId);
    setLoading(true);
  };

  const toggleMetric = (k: MetricKind) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(k)) {
        if (next.size > 1) next.delete(k); // keep at least one
      } else next.add(k);
      return next;
    });

  if (!isConnected) {
    return (
      <EmptyState
        icon={<PlugZap className="w-10 h-10" />}
        title="No AWS account connected"
        description="Connect an AWS account to explore metrics."
        action={
          <button
            onClick={() => navigate('/onboarding')}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
          >
            Connect AWS
          </button>
        }
      />
    );
  }

  const activeMetrics = METRICS.filter((m) => selected.has(m.key));
  const totalCount = resources.ec2.length + resources.rds.length + resources.lambda.length;

  return (
    <div>
      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Metrics Explorer</h1>
          <p className="text-gray-400 text-sm mt-1">
            Unified timeline · {region} · synchronized crosshair across panels
            {lastUpdated && (
              <span className="text-gray-600">
                {' '}
                · updated {new Date(lastUpdated).toLocaleTimeString('en-US', { hour12: false })}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setLive((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
              live
                ? 'border-emerald-600/40 text-emerald-300 bg-emerald-600/10'
                : 'border-gray-700 text-gray-400 hover:text-white'
            }`}
            title="Toggle 15s live refresh"
          >
            <Radio className={`w-4 h-4 ${live ? 'animate-pulse' : ''}`} />
            {live ? 'Live' : 'Paused'}
          </button>
          <button
            onClick={() => void load(true)}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-600 text-sm disabled:opacity-40"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-4 mb-5">
        <label className="flex flex-col gap-1 text-xs text-gray-400">
          Resource
          <select
            value={resource}
            onChange={(e) => handleResourceChange(e.target.value)}
            className="bg-[#0B0F17] border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white min-w-[260px]"
          >
            {totalCount === 0 && <option value="">No resources found in {region}</option>}

            {resources.ec2.length > 0 && (
              <optgroup label="EC2 Instances">
                {resources.ec2.map((r) => (
                  <option key={r.resourceId} value={r.resourceId}>
                    {r.name !== '—' ? `${r.name} (${r.resourceId})` : r.resourceId}
                  </option>
                ))}
              </optgroup>
            )}

            {resources.rds.length > 0 && (
              <optgroup label="RDS Databases">
                {resources.rds.map((r) => (
                  <option key={r.resourceId} value={r.resourceId}>
                    {r.name} (RDS)
                  </option>
                ))}
              </optgroup>
            )}

            {resources.lambda.length > 0 && (
              <optgroup label="Lambda Functions">
                {resources.lambda.map((r) => (
                  <option key={r.resourceId} value={r.resourceId}>
                    {r.name} (Lambda)
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </label>

        <div className="flex flex-col gap-1 text-xs text-gray-400">
          Metrics
          <div className="flex gap-1">
            {METRICS.map((m) => (
              <button
                key={m.key}
                onClick={() => toggleMetric(m.key)}
                className={`px-3 py-1.5 rounded-lg text-sm border ${
                  selected.has(m.key)
                    ? 'border-emerald-500 text-white bg-emerald-600/10'
                    : 'border-gray-700 text-gray-400 hover:text-white'
                }`}
              >
                {m.label.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-1 text-xs text-gray-400">
          Time range
          <div className="flex gap-1">
            {RANGES.map((r, i) => (
              <button
                key={r.label}
                onClick={() => setRangeIdx(i)}
                className={`px-3 py-1.5 rounded-lg text-sm border ${
                  rangeIdx === i
                    ? 'border-emerald-500 text-white bg-emerald-600/10'
                    : 'border-gray-700 text-gray-400 hover:text-white'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {loading && activeMetrics.every((m) => series[m.key].length === 0) ? (
        <div className="h-72 flex items-center justify-center">
          <Spinner label={`Querying metrics for ${resource || 'resource'}…`} />
        </div>
      ) : (
        <div className="space-y-4">
          {activeMetrics.map((m, idx) => (
            <MetricPanel
              key={m.key}
              label={m.label}
              unit={m.unit}
              color={m.color}
              kind={m.key}
              data={series[m.key]}
              showBrush={idx === activeMetrics.length - 1}
              rangeMinutes={range.minutes}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function MetricPanel({
  label,
  unit,
  color,
  data,
  showBrush,
  rangeMinutes,
}: {
  label: string;
  unit: string;
  color: string;
  kind: MetricKind;
  data: MetricPoint[];
  showBrush: boolean;
  rangeMinutes: number;
}) {
  const chartData = useMemo(
    () =>
      data.map((p) => {
        const d = new Date(p.t);
        const timeStr =
          rangeMinutes > 1440
            ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
              ' ' +
              d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
            : d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
        return {
          time: timeStr,
          value: p.value,
        };
      }),
    [data, rangeMinutes]
  );

  return (
    <Panel className="p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-white font-medium text-sm">
          <span className="inline-block w-2.5 h-2.5 rounded-full mr-2" style={{ background: color }} />
          {label}
          {unit && <span className="text-gray-500"> ({unit})</span>}
        </h2>
      </div>
      {chartData.length === 0 ? (
        <div className="h-40 flex items-center justify-center text-center">
          <div>
            <LineChart className="w-8 h-8 text-gray-600 mx-auto mb-2" />
            <p className="text-gray-500 text-sm">
              No data points found for this resource in the selected window.
            </p>
          </div>
        </div>
      ) : (
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <RLineChart data={chartData} syncId={SYNC_ID} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 11 }} minTickGap={40} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, color: '#fff' }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
              {showBrush && <Brush dataKey="time" height={20} stroke="#374151" fill="#0B0F17" travellerWidth={8} />}
            </RLineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
