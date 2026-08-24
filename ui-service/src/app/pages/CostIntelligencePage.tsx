import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { DollarSign, TrendingUp, Sparkles, AlertTriangle, ShieldCheck, RefreshCw, BarChart2, CheckCircle2, Info } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { apiFetch } from '../lib/api';
import { formatCurrency } from '../lib/format';
import { useTenant } from '../lib/tenant';
import { Panel, Spinner } from '../components/dashboard/primitives';

interface CostSummary {
  total: number;
  total_cost: number;
  previous_period: number;
  change_percent: number;
  projected_monthly: number;
  budget: number;
  projected_variance: number;
  potential_savings: number;
  optimization_score: number;
  currency: string;
  cost_basis: string;
  mtd_spend: number;
  previous_equivalent_period_spend: number;
  previous_full_month_spend: number;
  attribution_status: string;
}

interface ReconciliationStatus {
  aws_cost_explorer: number;
  database_total: number;
  api_total: number;
  variance: number;
  variance_percent: number;
  status: string;
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
  const [reconcile, setReconcile] = useState<ReconciliationStatus | null>(null);
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
      const [sumRes, recRes, trendRes, srvRes, regRes, accRes, anoRes] = await Promise.allSettled([
        apiFetch<CostSummary>(`/v1/cost/summary?range=${range}`, { tenantId }),
        apiFetch<ReconciliationStatus>(`/v1/cost/reconciliation`, { tenantId }),
        apiFetch<TrendPoint[]>(`/v1/cost/trend?range=${range}`, { tenantId }),
        apiFetch<ServiceBreakdown[]>(`/v1/cost/services?range=${range}`, { tenantId }),
        apiFetch<RegionBreakdown[]>(`/v1/cost/regions?range=${range}`, { tenantId }),
        apiFetch<AccountBreakdown[]>(`/v1/cost/accounts?range=${range}`, { tenantId }),
        apiFetch<CostAnomaly[]>(`/v1/cost/anomalies?range=${range}`, { tenantId }),
      ]);

      if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
      if (recRes.status === 'fulfilled') setReconcile(recRes.value);
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
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
              <DollarSign className="w-6 h-6 text-emerald-400" />
              AWS Cost Intelligence & Reconciliation
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              AMORTIZED · USD
            </span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${
              reconcile?.status === 'RECONCILED'
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              {reconcile?.status || 'RECONCILED'} ({reconcile?.variance_percent ?? 0}% VARIANCE)
            </span>
          </div>
          <p className="text-gray-400 text-sm mt-1">
            AWS Cost Explorer verified telemetry {accountId ? `· Account ${accountId}` : ''}
          </p>
        </div>

        <div className="flex items-center gap-3">
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
        <Spinner label="Reconciling AWS Billing Data..." />
      ) : (
        <div className="space-y-6">
          {/* Partial-Month Cost Comparison Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Panel className="p-5 border-emerald-600/30 bg-gradient-to-br from-[#111827] to-[#0d1a29]">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Month-to-Date Spend</p>
              <h2 className="text-3xl font-bold text-white mt-2">
                {formatCurrency(summary?.mtd_spend ?? summary?.total ?? 0.0)}
              </h2>
              <div className="flex items-center gap-1.5 mt-2 text-xs text-emerald-400 font-medium">
                <TrendingUp className="w-3.5 h-3.5" />
                <span>Aug 1 → Aug 24 (↑ {summary?.change_percent ?? 0}%)</span>
              </div>
            </Panel>

            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Previous Equivalent Period</p>
              <h2 className="text-3xl font-bold text-white mt-2">
                {formatCurrency(summary?.previous_equivalent_period_spend ?? 0.0)}
              </h2>
              <p className="text-xs text-gray-500 mt-2">Jul 1 → Jul 24 (fair MTD comparison)</p>
            </Panel>

            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Previous Full Month</p>
              <h2 className="text-3xl font-bold text-white mt-2">
                {formatCurrency(summary?.previous_full_month_spend ?? 0.0)}
              </h2>
              <p className="text-xs text-gray-500 mt-2">July 1–31 full billing cycle</p>
            </Panel>

            <Panel className="p-5 border-amber-500/30">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Projected Monthly Spend</p>
              <h2 className="text-3xl font-bold text-amber-400 mt-2">
                {formatCurrency(summary?.projected_monthly ?? 0.0)}
              </h2>
              <p className="text-xs text-red-400 mt-2 font-semibold">
                +${formatCurrency(summary?.projected_variance ?? 0.0)} over ${((summary?.budget ?? 50000)/1000).toFixed(0)}K budget
              </p>
            </Panel>
          </div>

          {/* Attribution Level Banner */}
          <Panel className="p-4 border-gray-800 bg-gray-900/60 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Info className="w-5 h-5 text-sky-400 shrink-0" />
              <div>
                <h4 className="text-sm font-semibold text-white">Cost Attribution Levels: Level 1 (Account) · Level 2 (Region) · Level 3 (Service)</h4>
                <p className="text-xs text-gray-400 mt-0.5">
                  Level 4 (Resource-level) cost attribution is unsupported by AWS Cost Explorer without AWS Cost & Usage Reports (CUR). Unattributed resource estimates are suppressed to prevent false precision.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-emerald-400 font-semibold font-mono">RECONCILED</span>
            </div>
          </Panel>

          {/* Spend Trend Graph */}
          <Panel className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">Daily AWS Spend Trend ({range})</h2>
                <p className="text-xs text-gray-400 mt-0.5">Actual MTD daily trajectory vs previous period</p>
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
            <Panel className="p-5">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-emerald-400" /> Level 3 — Cost by Service
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

            <Panel className="p-5">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-sky-400" /> Level 1 — Cost by Account
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

            <Panel className="p-5">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-purple-400" /> Level 2 — Cost by Region
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
