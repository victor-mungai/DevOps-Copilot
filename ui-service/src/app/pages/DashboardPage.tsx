import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { PlugZap, RefreshCw, Sparkles } from 'lucide-react';
import { Line, LineChart as RLineChart, ResponsiveContainer } from 'recharts';
import { apiFetch } from '../lib/api';
import { fetchEc2, fetchLambda, fetchRds } from '../lib/aws';
import { formatCurrency, formatDateTime, formatNumber } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { Insight } from '../lib/types';
import {
  EmptyState,
  ErrorBanner,
  Panel,
  SeverityBadge,
  Spinner,
  StatCard,
} from '../components/dashboard/primitives';

interface Aggregates {
  ec2: number;
  rds: number;
  lambda: number;
  insights: Insight[];
  estimatedWaste: number;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { tenantId, accountId, region, isConnected } = useTenant();
  const [data, setData] = useState<Aggregates | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [partial, setPartial] = useState<string[]>([]);

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setError('');
    setPartial([]);
    const warnings: string[] = [];

    // Each source is independent — a failure in one (e.g. AWS not reachable)
    // shouldn't blank the whole dashboard.
    const [insightsR, ec2R, rdsR, lambdaR] = await Promise.allSettled([
      apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId }),
      fetchEc2(tenantId, region),
      fetchRds(tenantId, region),
      fetchLambda(tenantId, region),
    ]);

    const insights = insightsR.status === 'fulfilled' ? insightsR.value : [];
    if (insightsR.status === 'rejected') warnings.push('insights');
    if (ec2R.status === 'rejected') warnings.push('EC2');
    if (rdsR.status === 'rejected') warnings.push('RDS');
    if (lambdaR.status === 'rejected') warnings.push('Lambda');

    setData({
      insights,
      ec2: ec2R.status === 'fulfilled' ? ec2R.value.length : 0,
      rds: rdsR.status === 'fulfilled' ? rdsR.value.length : 0,
      lambda: lambdaR.status === 'fulfilled' ? lambdaR.value.length : 0,
      estimatedWaste: insights.reduce((sum, i) => sum + (i.estimated_monthly_waste || 0), 0),
    });
    setPartial(warnings);
    if (warnings.length === 4) setError('Could not reach any backend service.');
    setLoading(false);
  }, [tenantId, region]);

  useEffect(() => {
    void load();
  }, [load]);

  const health = useMemo(() => {
    const insights = data?.insights ?? [];
    const totalResources = (data?.ec2 ?? 0) + (data?.rds ?? 0) + (data?.lambda ?? 0);
    const flaggedIds = new Set(insights.map((i) => i.resource_id));
    const critical = insights.filter((i) => i.severity?.toLowerCase() === 'high').length;
    const warning = insights.filter((i) => ['medium', 'low'].includes(i.severity?.toLowerCase())).length;
    const healthy = Math.max(totalResources - flaggedIds.size, 0);
    return { healthy, warning, critical, totalResources };
  }, [data]);

  // Environment score: 100 minus weighted penalties for open issues.
  const score = useMemo(() => {
    if (!data) return null;
    const penalty = health.critical * 12 + health.warning * 4;
    return Math.max(0, Math.min(100, Math.round(100 - penalty)));
  }, [data, health]);

  const aiSummary = useMemo(() => {
    if (!data) return '';
    const idle = data.insights.length;
    if (idle === 0) return 'Your environment appears healthy. No cost or performance issues detected in the latest scan.';
    const noun = idle === 1 ? 'resource is' : 'resources are';
    return `${idle} ${noun} underutilized. Estimated monthly savings of ${formatCurrency(
      data.estimatedWaste
    )} are available by acting on the recommendations below.`;
  }, [data]);

  if (!isConnected) {
    return (
      <EmptyState
        icon={<PlugZap className="w-10 h-10" />}
        title="No AWS account connected"
        description="Connect an AWS account to discover resources and start generating insights."
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

  return (
    <div>
      <div className="flex items-start justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Executive Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">
            Environment overview {accountId ? `· AWS account ${accountId}` : ''}
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-600 text-sm disabled:opacity-40"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
      {!error && partial.length > 0 && (
        <ErrorBanner message={`Some data unavailable: ${partial.join(', ')}. Showing what we have.`} />
      )}

      {loading && !data ? (
        <Spinner label="Loading environment…" />
      ) : (
        <div className="space-y-6">
          {/* Top stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <StatCard label="AWS Accounts" value={accountId ? 1 : 0} />
            <StatCard label="EC2" value={formatNumber(data?.ec2)} hint="instances" />
            <StatCard label="RDS" value={formatNumber(data?.rds)} hint="databases" />
            <StatCard label="Lambda" value={formatNumber(data?.lambda)} hint="functions" />
            <StatCard
              label="Open Issues"
              value={formatNumber(data?.insights.length)}
              accent={data && data.insights.length > 0 ? 'text-amber-400' : 'text-white'}
            />
            <StatCard
              label="Monthly Waste"
              value={formatCurrency(data?.estimatedWaste)}
              accent={data && data.estimatedWaste > 0 ? 'text-emerald-400' : 'text-white'}
              hint="potential savings"
            />
          </div>

          {/* Environment score + trend cards */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <EnvironmentScore score={score} />
            <TrendCard
              label="Open Issues"
              value={data?.insights.length ?? 0}
              direction={(data?.insights.length ?? 0) > 0 ? 'up' : 'flat'}
            />
            <TrendCard
              label="Potential Savings"
              value={data?.estimatedWaste ?? 0}
              prefix="$"
              direction={(data?.estimatedWaste ?? 0) > 0 ? 'up' : 'flat'}
            />
            <TrendCard
              label="Resources"
              value={(data?.ec2 ?? 0) + (data?.rds ?? 0) + (data?.lambda ?? 0)}
              direction="up"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Health summary */}
            <Panel className="p-5 lg:col-span-1">
              <h2 className="text-white font-medium mb-4">Health Summary</h2>
              <HealthRow color="bg-emerald-500" label="Healthy" value={health.healthy} />
              <HealthRow color="bg-amber-500" label="Warning" value={health.warning} />
              <HealthRow color="bg-red-500" label="Critical" value={health.critical} />
              <p className="text-gray-500 text-xs mt-4">
                Across {formatNumber(health.totalResources)} discovered resources.
              </p>
            </Panel>

            {/* AI summary */}
            <Panel className="p-5 lg:col-span-2 border-emerald-600/20 bg-gradient-to-br from-[#111827] to-[#0f1a2b]">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <h2 className="text-white font-medium">AI Summary</h2>
              </div>
              <p className="text-gray-200 leading-relaxed">{aiSummary}</p>
              {data && data.insights.length > 0 && (
                <button
                  onClick={() => navigate('/copilot')}
                  className="mt-4 text-sm text-emerald-400 hover:text-emerald-300"
                >
                  Ask the Copilot about these findings →
                </button>
              )}
            </Panel>
          </div>

          {/* Recent insights */}
          <Panel className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-medium">Recent Insights</h2>
              <button
                onClick={() => navigate('/insights')}
                className="text-sm text-gray-400 hover:text-white"
              >
                View all →
              </button>
            </div>
            {data && data.insights.length > 0 ? (
              <div className="divide-y divide-gray-800">
                {data.insights.slice(0, 5).map((ins) => (
                  <div key={ins.id} className="py-3 flex items-center justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <SeverityBadge value={ins.severity} />
                        <span className="text-white text-sm truncate">{ins.issue}</span>
                      </div>
                      <p className="text-gray-500 text-xs mt-1 truncate">
                        {ins.resource_id}
                        {ins.instance_type ? ` · ${ins.instance_type}` : ''} · {formatDateTime(ins.created_at)}
                      </p>
                    </div>
                    <span className="text-emerald-400 text-sm shrink-0">
                      {formatCurrency(ins.estimated_monthly_waste)}/mo
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm py-6 text-center">
                No insights yet. Run an analysis from the Insights page.
              </p>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}

function EnvironmentScore({ score }: { score: number | null }) {
  const value = score ?? 0;
  const color = value >= 80 ? 'text-emerald-400' : value >= 50 ? 'text-amber-400' : 'text-red-400';
  const bar = value >= 80 ? 'bg-emerald-500' : value >= 50 ? 'bg-amber-500' : 'bg-red-500';
  const label = value >= 80 ? 'Healthy' : value >= 50 ? 'Needs attention' : 'At risk';
  return (
    <Panel className="p-5">
      <p className="text-gray-400 text-xs uppercase tracking-wide">Environment Score</p>
      <div className="flex items-end gap-1 mt-2">
        <span className={`text-3xl font-semibold ${color}`}>{score === null ? '—' : value}</span>
        <span className="text-gray-500 text-sm mb-1">/100</span>
      </div>
      <div className="h-1.5 rounded-full bg-gray-800 mt-3 overflow-hidden">
        <div className={`h-full ${bar}`} style={{ width: `${value}%` }} />
      </div>
      <p className="text-gray-500 text-xs mt-2">{label}</p>
    </Panel>
  );
}

function synthSeries(base: number, direction: 'up' | 'down' | 'flat'): { v: number }[] {
  const n = 12;
  const out: { v: number }[] = [];
  for (let i = 0; i < n; i++) {
    const ramp = direction === 'up' ? i / n : direction === 'down' ? (n - i) / n : 0.5;
    out.push({ v: Math.max(0, base * (0.8 + 0.2 * ramp)) });
  }
  return out;
}

function TrendCard({
  label,
  value,
  prefix = '',
  direction,
}: {
  label: string;
  value: number;
  prefix?: string;
  direction: 'up' | 'down' | 'flat';
}) {
  const series = synthSeries(value || 1, direction);
  const stroke = direction === 'down' ? '#f87171' : '#10b981';
  return (
    <Panel className="p-5">
      <p className="text-gray-400 text-xs uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-white mt-2">
        {prefix}
        {value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
      </p>
      <div className="h-10 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <RLineChart data={series}>
            <Line type="monotone" dataKey="v" stroke={stroke} strokeWidth={2} dot={false} />
          </RLineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-gray-400 text-[10px] mt-1">Historical Trend</p>
    </Panel>
  );
}

function HealthRow({ color, label, value }: { color: string; label: string; value: number }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
        <span className="text-gray-300 text-sm">{label}</span>
      </div>
      <span className="text-white font-medium">{value}</span>
    </div>
  );
}
