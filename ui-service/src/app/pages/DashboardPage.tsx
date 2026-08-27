import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowUpRight, RefreshCw, Server, PiggyBank, Layers, AlertTriangle } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { fetchEc2, fetchLambda, fetchRds } from '../lib/aws';
import { formatCurrency } from '../lib/format';
import { periodQuery, useTenant } from '../lib/tenant';
import { fetchForScope, mergeBreakdown, mergeSummaries, mergeTrends, scopedTenantIds } from '../lib/costScope';
import type { Insight } from '../lib/types';

export function DashboardPage() {
  const navigate = useNavigate();
  const { tenantId, tenantName, accountId, region, isConnected, timePeriod, customRange, isAllAccounts, scopeLabel, workspaces } = useTenant();
  const [loading, setLoading] = useState(false);

  const [summary, setSummary] = useState<any>(null);
  const [services, setServices] = useState<any[]>([]);
  const [trend, setTrend] = useState<any[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [resourcesCount, setResourcesCount] = useState<number>(0);
  const [expandedOppId, setExpandedOppId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const regParamAmp = region ? `&region=${encodeURIComponent(region)}` : '';
      const rangeParam = periodQuery(timePeriod, customRange);
      const tenantIds = scopedTenantIds(tenantId, isAllAccounts, workspaces);
      const scoped = <T,>(path: string) => isAllAccounts ? fetchForScope<T>(tenantIds, path, [] as T[]) : apiFetch<T>(path, { tenantId });

      const [sumR, drvR, trdR, insR, oppR, ec2R, rdsR, lmbR] = await Promise.allSettled([
        scoped<any>(`/v1/cost/summary?${rangeParam}&basis=NET_UNBLENDED${regParamAmp}`),
        scoped<any>(`/v1/cost/services?${rangeParam}${regParamAmp}`),
        scoped<any>(`/v1/cost/trend?${rangeParam}${regParamAmp}`),
        isAllAccounts
          ? fetchForScope<Insight>(tenantIds, `/v1/insights/{tenant_id}?limit=20${regParamAmp}`, [] as Insight[])
          : apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=20${regParamAmp}`, { tenantId }),
        scoped<any>(`/v1/cost/opportunities`),
        isAllAccounts ? Promise.resolve([]) : fetchEc2(tenantId, region),
        isAllAccounts ? Promise.resolve([]) : fetchRds(tenantId, region),
        isAllAccounts ? Promise.resolve([]) : fetchLambda(tenantId, region),
      ]);

      if (sumR.status === 'fulfilled') setSummary(isAllAccounts ? mergeSummaries(sumR.value as any[]) : sumR.value);
      if (drvR.status === 'fulfilled') {
        const value = drvR.value;
        setServices(isAllAccounts ? mergeBreakdown(value as any[], 'services') : (Array.isArray(value) ? value : (value?.services || [])));
      }
      if (trdR.status === 'fulfilled') setTrend(isAllAccounts ? mergeTrends(trdR.value as any[]) : (Array.isArray(trdR.value) ? trdR.value : []));
      if (insR.status === 'fulfilled') setInsights(isAllAccounts ? (insR.value as any[]).flatMap((value) => Array.isArray(value) ? value : []) : (Array.isArray(insR.value) ? insR.value : []));
      if (oppR.status === 'fulfilled') setOpportunities(isAllAccounts ? (oppR.value as any[]).flatMap((value) => value?.opportunities || []) : (Array.isArray(oppR.value) ? oppR.value : (oppR.value?.opportunities || [])));

      const ec2Cnt = ec2R.status === 'fulfilled' ? ec2R.value.length : 0;
      const rdsCnt = rdsR.status === 'fulfilled' ? rdsR.value.length : 0;
      const lmbCnt = lmbR.status === 'fulfilled' ? lmbR.value.length : 0;
      setResourcesCount(ec2Cnt + rdsCnt + lmbCnt);
    } catch (err) {
      console.error('Failed to load overview:', err);
    } finally {
      setLoading(false);
    }
  }, [tenantId, region, timePeriod, customRange, isAllAccounts, workspaces]);

  useEffect(() => {
    void load();
  }, [load]);

  const highCount = useMemo(() => insights.filter((i) => (i.severity || '').toLowerCase() === 'high').length, [insights]);
  const mediumCount = useMemo(() => insights.filter((i) => (i.severity || '').toLowerCase() === 'medium').length, [insights]);
  const lowCount = useMemo(() => insights.filter((i) => (i.severity || '').toLowerCase() === 'low').length, [insights]);

  const totalSavings = opportunities.reduce((acc, o) => acc + (o.estimated_monthly_waste || o.potential_saving_monthly || 0), 0);

  if (!isConnected) {
    return (
      <div className="py-16 text-center">
        <Server className="w-10 h-10 text-gray-600 mx-auto mb-3" />
        <h2 className="text-lg font-semibold text-white">No AWS account connected</h2>
        <p className="text-gray-400 text-sm mt-1 mb-6 max-w-sm mx-auto">
          Connect your AWS account to monitor infrastructure, performance, and costs.
        </p>
        <button
          onClick={() => navigate('/onboarding')}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
        >
          Connect AWS
        </button>
      </div>
    );
  }

  const grossSpend = summary?.gross ?? 0;
  const creditsSpend = summary?.adjustments ?? summary?.total_credits_and_discounts ?? summary?.credits ?? 0;
  const netSpend = summary?.net ?? summary?.total_cost ?? summary?.gross ?? 0;
  const changePct = summary?.change_percent ?? 0;
  const burnRateDaily = trend.length > 0 ? (netSpend / Math.max(1, trend.length)) : netSpend / 30;

  const pStart = summary?.period?.start;
  const pEnd = summary?.period?.end;
  const periodLabel = pStart && pEnd ? `${pStart} – ${pEnd}` : scopeLabel;

  return (
    <div className="space-y-8 font-sans">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Overview</h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400 mt-1">
            <span className="text-white font-medium">{tenantName}</span>
            <span>·</span>
            <span>AWS Account {accountId}</span>
            <span>·</span>
            <span className="text-gray-400">{region}</span>
            <span>·</span>
            <span className="text-emerald-400 font-medium bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 text-xs font-mono">
              {scopeLabel}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => void load()}
            disabled={loading}
            className="p-1.5 rounded-lg border border-gray-800 text-gray-400 hover:text-white hover:border-gray-700 disabled:opacity-40"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Executive Financial Ledger Banner */}
      <div className="rounded-xl bg-[#111827] border border-gray-800 p-6 space-y-4 font-sans">
        <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-400">FINANCIAL SUMMARY</h2>
            <p className="text-sm font-semibold text-white mt-0.5">{periodLabel}</p>
          </div>
          <span className="text-xs text-gray-400 font-mono bg-gray-900 px-2.5 py-1 rounded border border-gray-800">
            Source: AWS Cost Explorer
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          {/* Gross Spend */}
          <div className="p-4 rounded-lg bg-[#0B0F17] border border-gray-800">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 block">Gross Spend</span>
            <span className="text-2xl font-bold text-white mt-1 block">{formatCurrency(grossSpend)}</span>
            <span className="text-xs text-gray-500 mt-1 block">Raw usage/charges before credits</span>
          </div>

          {/* AWS Credits */}
          <div className="p-4 rounded-lg bg-[#0B0F17] border border-gray-800">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 block">AWS Credits and Discounts</span>
            <span className="text-2xl font-bold text-emerald-400 mt-1 block">
              {creditsSpend === 0 ? '$0.00' : `-${formatCurrency(Math.abs(creditsSpend))}`}
            </span>
            <span className="text-xs text-emerald-500/80 mt-1 block">Signed credits, refunds, and discounts</span>
          </div>

          {/* Net Spend */}
          <div className="p-4 rounded-lg bg-[#0B0F17] border border-gray-800">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 block">Net Spend</span>
            <span className="text-2xl font-bold text-white mt-1 block">{formatCurrency(netSpend)}</span>
            <span className="text-xs text-gray-500 mt-1 block">Resulting net payable spend</span>
          </div>
        </div>
      </div>

      {/* 6 Top-Level FinOps Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {/* Total Spend */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-4 flex flex-col justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">TOTAL SPEND</p>
          <p className="text-xl font-bold text-white mt-1">{formatCurrency(netSpend)}</p>
          <span className="text-[10px] text-gray-500 mt-1 font-mono">{timePeriod.toUpperCase()}</span>
        </div>

        {/* MoM Change */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-4 flex flex-col justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">MOM CHANGE</p>
          <p className={`text-xl font-bold mt-1 ${changePct >= 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {changePct >= 0 ? '↑' : '↓'} {Math.abs(changePct)}%
          </p>
          <span className="text-[10px] text-gray-500 mt-1">vs prev period</span>
        </div>

        {/* Burn Rate */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-4 flex flex-col justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">BURN RATE</p>
          <p className="text-xl font-bold text-white mt-1">{formatCurrency(burnRateDaily)}</p>
          <span className="text-[10px] text-gray-500 mt-1">per day avg</span>
        </div>

        {/* Potential Savings */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-4 flex flex-col justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">SAVINGS</p>
          <p className="text-xl font-bold text-emerald-400 mt-1">{formatCurrency(totalSavings)}</p>
          <span className="text-[10px] text-emerald-500/80 mt-1">potential / mo</span>
        </div>

        {/* AWS Accounts */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-4 flex flex-col justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">AWS ACCOUNTS</p>
          <p className="text-xl font-bold text-white mt-1">{isAllAccounts ? workspaces.length : 1}</p>
          <span className="text-[10px] text-gray-500 mt-1">{isAllAccounts ? 'All connected' : 'Active account'}</span>
        </div>

        {/* Cost Issues */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-4 flex flex-col justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">ISSUES</p>
          <p className="text-xl font-bold text-amber-400 mt-1">{highCount + mediumCount}</p>
          <span className="text-[10px] text-gray-500 mt-1">{highCount} High priority</span>
        </div>
      </div>

      {/* Cost Trend Chart */}
      <div className="rounded-xl bg-[#111827] border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase">COST TREND</h2>
            <p className="text-xs text-gray-500 mt-0.5">Actual AWS cost time-series · {scopeLabel}</p>
          </div>
          <button
            onClick={() => navigate('/cost-intelligence')}
            className="text-xs text-emerald-400 hover:underline flex items-center gap-1"
          >
            Full cost analysis <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {trend.length === 0 ? (
          <div className="h-32 flex items-center justify-center text-xs text-gray-500">
            No daily trend points recorded for this scope.
          </div>
        ) : (
          <div className="h-44 w-full pt-4">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 800 120" preserveAspectRatio="none">
              <path
                d={buildDynamicSvgPath(trend)}
                fill="none"
                stroke="#10B981"
                strokeWidth="2.5"
              />
            </svg>
            <div className="flex justify-between text-xs text-gray-500 pt-2 border-t border-gray-800">
              {trend.slice(0, 5).map((t, idx) => (
                <span key={idx}>{t.date || `Point ${idx + 1}`}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Grid: Top Cost Drivers & Savings Opportunities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Cost Drivers */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase">TOP COST DRIVERS</h2>
            <span className="text-xs text-gray-500 font-mono">{timePeriod.toUpperCase()}</span>
          </div>
          {services.length === 0 ? (
            <p className="text-xs text-gray-500 py-4 text-center">No cost driver breakdown available.</p>
          ) : (
            <div className="space-y-3">
              {services.slice(0, 5).map((srv, idx) => (
                <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-800/60 last:border-0 text-sm">
                  <span className="font-medium text-white">{srv.service || srv.name}</span>
                  <div className="text-right">
                    <span className="font-mono text-gray-200 block">{formatCurrency(srv.gross || srv.cost || 0)}</span>
                    <span className="text-xs text-emerald-400 font-mono block">{srv.gross_percentage ?? srv.percentage ?? 0}% of gross</span>
                    {(srv.credits ?? 0) !== 0 && (
                      <span className="text-[10px] text-emerald-400 font-mono">Credit: -{formatCurrency(Math.abs(srv.credits))}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Savings Opportunities */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase">SAVINGS OPPORTUNITIES</h2>
            <button
              onClick={() => navigate('/savings')}
              className="text-xs text-emerald-400 hover:underline flex items-center gap-1"
            >
              All savings <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {opportunities.length === 0 ? (
            <p className="text-xs text-gray-500 py-4 text-center">No savings opportunities identified.</p>
          ) : (
            <div className="space-y-3">
              {opportunities.slice(0, 4).map((opp, idx) => {
                const oppId = opp.id || `opp-${idx}`;
                const isExpanded = expandedOppId === oppId;
                const savings = opp.estimated_monthly_waste || opp.potential_saving_monthly || 0;
                return (
                  <div key={oppId} className="rounded-lg bg-[#0B0F17] border border-gray-800/80 p-3 space-y-2 text-xs">
                    <div
                      onClick={() => setExpandedOppId(isExpanded ? null : oppId)}
                      className="flex items-center justify-between cursor-pointer"
                    >
                      <span className="font-semibold text-white">{opp.title || opp.name}</span>
                      <span className="font-semibold text-emerald-400">{formatCurrency(savings)}/mo saving</span>
                    </div>

                    {isExpanded && (
                      <div className="pt-2 border-t border-gray-800 space-y-1 text-[11px] text-gray-400">
                        <p><span className="text-gray-300 font-medium">Resource:</span> {opp.resource_id}</p>
                        <p><span className="text-gray-300 font-medium">Account:</span> {opp.account || tenantId}</p>
                        <p><span className="text-gray-300 font-medium">Evidence:</span> {opp.evidence || 'AWS telemetry scan'}</p>
                        <p><span className="text-emerald-400 font-medium">Recommendation:</span> {opp.recommendation || 'Stop or resize resource'}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function buildDynamicSvgPath(trend: any[], width = 800, height = 120): string {
  if (!trend || trend.length === 0) return 'M0,100 L800,100';
  const costs = trend.map((t) => Number(t.net ?? t.cost ?? t.gross ?? 0));
  const maxCost = Math.max(...costs, 0.00001);
  const minCost = Math.min(...costs, 0);
  const range = Math.max(maxCost - minCost, 0.00001);

  const points = trend.map((t, idx) => {
    const x = (idx / Math.max(1, trend.length - 1)) * width;
    const val = Number(t.net ?? t.cost ?? t.gross ?? 0);
    const y = height - ((val - minCost) / range) * (height - 20) - 10;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return `M${points.join(' L')}`;
}
