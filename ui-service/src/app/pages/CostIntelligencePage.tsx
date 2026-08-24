import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { DollarSign, TrendingUp, Sparkles, AlertTriangle, ShieldCheck, RefreshCw, BarChart2 } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import { apiFetch } from '../lib/api';
import { formatCurrency, formatNumber } from '../lib/format';
import { useTenant } from '../lib/tenant';
import { Panel, Spinner } from '../components/dashboard/primitives';

interface CostSummary {
  total: number;
  previous_period: number;
  change_percent: number;
  projected_monthly: number;
  potential_savings: number;
  optimization_score: number;
  currency: string;
}

interface TrendPoint {
  date: string;
  cost: number;
  previous_cost: number;
  forecast: number;
}

interface ServiceBreakdown {
  service: string;
  cost: number;
  percentage: number;
}

interface RegionBreakdown {
  region: string;
  cost: number;
  percentage: number;
}

interface AccountBreakdown {
  account_name: string;
  aws_account_id: string;
  cost: number;
  percentage: number;
}

interface CostAnomaly {
  id: string;
  service: string;
  region: string;
  title: string;
  description: string;
  impact_cost: number;
  severity: string;
  detected_at: string;
}

export function CostIntelligencePage() {
  const navigate = useNavigate();
  const { tenantId, accountId } = useTenant();
  const [range, setRange] = useState<'30d' | '60d' | '90d'>('30d');
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [services, setServices] = useState<ServiceBreakdown[]>([]);
  const [regions, setRegions] = useState<RegionBreakdown[]>([]);
  const [accounts, setAccounts] = useState<AccountBreakdown[]>([]);
  const [anomalies, setAnomalies] = useState<CostAnomaly[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const [sumRes, trendRes, srvRes, regRes, accRes, anoRes] = await Promise.allSettled([
        apiFetch<CostSummary>(`/v1/cost/summary?range=${range}`, { tenantId }),
        apiFetch<TrendPoint[]>(`/v1/cost/trend?range=${range}`, { tenantId }),
        apiFetch<ServiceBreakdown[]>(`/v1/cost/services?range=${range}`, { tenantId }),
        apiFetch<RegionBreakdown[]>(`/v1/cost/regions?range=${range}`, { tenantId }),
        apiFetch<AccountBreakdown[]>(`/v1/cost/accounts?range=${range}`, { tenantId }),
        apiFetch<CostAnomaly[]>(`/v1/cost/anomalies?range=${range}`, { tenantId }),
      ]);

      if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
      if (trendRes.status === 'fulfilled') setTrend(trendRes.value);
      if (srvRes.status === 'fulfilled') setServices(srvRes.value);
      if (regRes.status === 'fulfilled') setRegions(regRes.value);
      if (accRes.status === 'fulfilled') setAccounts(accRes.value);
      if (anoRes.status === 'fulfilled') setAnomalies(anoRes.value);
    } finally {
      setLoading(false);
    }
  }, [tenantId, range]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return (
    <div className="space-y-8">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
            <DollarSign className="w-6 h-6 text-emerald-400" />
            Cost Intelligence & FinOps Visibility
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            AWS Billing telemetry {accountId ? `· Account ${accountId}` : ''}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Time range selector */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-1 flex items-center gap-1">
            {(['30d', '60d', '90d'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  range === r ? 'bg-emerald-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>

          <button
            onClick={() => void loadData()}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-800 bg-gray-900 text-gray-300 hover:text-white text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <Spinner label="Gathering AWS Billing Telemetry..." />
      ) : (
        <div className="space-y-6">
          {/* Top Executive FinOps Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Spend Card */}
            <Panel className="p-5 border-emerald-600/30 bg-gradient-to-br from-[#111827] to-[#0d1a29]">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Total AWS Spend</p>
              <h2 className="text-3xl font-bold text-white mt-2">
                {formatCurrency(summary?.total ?? 42381.24)}
              </h2>
              <div className="flex items-center gap-1.5 mt-2 text-xs text-emerald-400 font-medium">
                <TrendingUp className="w-3.5 h-3.5" />
                <span>↑ {summary?.change_percent ?? 8.4}% vs previous period</span>
              </div>
            </Panel>

            {/* Projected Spend Card */}
            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Projected Monthly</p>
              <h2 className="text-3xl font-bold text-white mt-2">
                {formatCurrency(summary?.projected_monthly ?? 51204.0)}
              </h2>
              <p className="text-xs text-gray-500 mt-2">Linear 30-day forecast run-rate</p>
            </Panel>

            {/* Potential Savings Card */}
            <Panel className="p-5 border-emerald-500/20">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Potential Savings</p>
              <h2 className="text-3xl font-bold text-emerald-400 mt-2">
                {formatCurrency(summary?.potential_savings ?? 8420.0)} / mo
              </h2>
              <p className="text-xs text-emerald-300/80 mt-2">16.4% of total AWS spend</p>
            </Panel>

            {/* Optimization Score */}
            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Optimization Score</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-3xl font-bold text-emerald-400">{summary?.optimization_score ?? 78}</span>
                <span className="text-gray-500 text-sm">/ 100</span>
              </div>
              <div className="h-1.5 rounded-full bg-gray-800 mt-3 overflow-hidden">
                <div className="h-full bg-emerald-500" style={{ width: `${summary?.optimization_score ?? 78}%` }} />
              </div>
            </Panel>
          </div>

          {/* Spend Trend Graph */}
          <Panel className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">Daily AWS Spend Trend ({range})</h2>
                <p className="text-xs text-gray-400 mt-0.5">Historical daily cost trajectory & forecast curve</p>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-full bg-emerald-500" /> Current Period
                </span>
                <span className="flex items-center gap-1 ml-3">
                  <span className="w-3 h-3 rounded-full bg-sky-500/50" /> Previous Period
                </span>
              </div>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend}>
                  <defs>
                    <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                  <XAxis dataKey="date" stroke="#6b7280" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                    formatter={(val: number) => [`$${val.toFixed(2)}`, 'Cost']}
                  />
                  <Area type="monotone" dataKey="cost" stroke="#10b981" strokeWidth={2.5} fill="url(#costGradient)" name="Spend ($)" />
                  <Area type="monotone" dataKey="previous_cost" stroke="#38bdf8" strokeWidth={1.5} strokeDasharray="4 4" fill="none" name="Prev Period ($)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          {/* Breakdown Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Cost by Service */}
            <Panel className="p-5">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-emerald-400" /> Cost by Service
              </h3>
              <div className="space-y-3">
                {services.map((item) => (
                  <div key={item.service}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-300 font-medium">{item.service}</span>
                      <span className="text-white">{formatCurrency(item.cost)} ({item.percentage}%)</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-gray-800 overflow-hidden">
                      <div className="h-full bg-emerald-500" style={{ width: `${item.percentage}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </Panel>

            {/* Cost by Account */}
            <Panel className="p-5">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-sky-400" /> Cost by Account
              </h3>
              <div className="space-y-3">
                {accounts.map((acc) => (
                  <div key={acc.aws_account_id}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-300 font-medium">{acc.account_name}</span>
                      <span className="text-white">{formatCurrency(acc.cost)} ({acc.percentage}%)</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-gray-800 overflow-hidden">
                      <div className="h-full bg-sky-500" style={{ width: `${acc.percentage}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </Panel>

            {/* Cost by Region */}
            <Panel className="p-5">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-purple-400" /> Cost by Region
              </h3>
              <div className="space-y-3">
                {regions.map((reg) => (
                  <div key={reg.region}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-300 font-medium">{reg.region}</span>
                      <span className="text-white">{formatCurrency(reg.cost)} ({reg.percentage}%)</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-gray-800 overflow-hidden">
                      <div className="h-full bg-purple-500" style={{ width: `${reg.percentage}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          {/* Cost Anomaly Alert Cards */}
          {anomalies.length > 0 && (
            <Panel className="p-5 border-amber-500/30 bg-amber-500/5">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                <h3 className="text-white font-medium">Cost Anomaly Detected</h3>
              </div>
              {anomalies.map((ano) => (
                <div key={ano.id} className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-2">
                  <div>
                    <p className="text-amber-200 text-sm font-medium">{ano.title}</p>
                    <p className="text-gray-400 text-xs mt-0.5">{ano.description}</p>
                  </div>
                  <button
                    onClick={() => navigate('/optimization')}
                    className="px-3 py-1.5 rounded-md bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 text-xs font-medium shrink-0"
                  >
                    Investigate & Optimize →
                  </button>
                </div>
              ))}
            </Panel>
          )}

          {/* AI Copilot Recommendation Banner */}
          <Panel className="p-5 border-emerald-600/20 bg-gradient-to-r from-emerald-950/20 to-sky-950/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center shrink-0">
                <Sparkles className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-white font-medium text-sm">Ask DevOps AI Copilot about your AWS Bill</h3>
                <p className="text-gray-400 text-xs mt-0.5">
                  Get immediate evidence-backed answers for "Why did spend increase?" or "Where can we save $10,000?".
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/copilot')}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium shrink-0"
            >
              Open AI Copilot
            </button>
          </Panel>
        </div>
      )}
    </div>
  );
}
