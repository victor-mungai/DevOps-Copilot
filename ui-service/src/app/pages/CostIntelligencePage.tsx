import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, ChevronRight, Layers, DollarSign } from 'lucide-react';
import { Brush, CartesianGrid, Line, LineChart as RLineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { apiFetch } from '../lib/api';
import { formatCurrency } from '../lib/format';
import { periodQuery, useTenant } from '../lib/tenant';
import { fetchForScope, mergeBreakdown, mergeSummaries, mergeTrends, scopedTenantIds } from '../lib/costScope';

export function CostIntelligencePage() {
  const { tenantId, region, isConnected, timePeriod, customRange, isAllAccounts, scopeLabel, workspaces } = useTenant();
  const [loading, setLoading] = useState(false);

  const [summary, setSummary] = useState<any>(null);
  const [accountsCost, setAccountsCost] = useState<any[]>([]);
  const [topServices, setTopServices] = useState<any[]>([]);
  const [trend, setTrend] = useState<any[]>([]);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [drilldown, setDrilldown] = useState<any>(null);

  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const regParamAmp = region ? `&region=${encodeURIComponent(region)}` : '';
      const rangeParam = periodQuery(timePeriod, customRange);
      const tenantIds = scopedTenantIds(tenantId, isAllAccounts, workspaces);
      const scoped = <T,>(path: string) => isAllAccounts ? fetchForScope<T>(tenantIds, path, [] as T[]) : apiFetch<T>(path, { tenantId });

      let drillUrl = `/v1/cost/drilldown?${rangeParam}${regParamAmp}`;
      if (selectedService) drillUrl += `&service=${encodeURIComponent(selectedService)}`;
      if (selectedRegion) drillUrl += `&region=${encodeURIComponent(selectedRegion)}`;
      const [sumRes, accRes, srvRes, trdRes, oppRes, drlRes] = await Promise.allSettled([
        scoped<any>(`/v1/cost/summary?${rangeParam}&basis=NET_UNBLENDED${regParamAmp}`),
        scoped<any>(`/v1/cost/accounts?${rangeParam}${regParamAmp}`),
        scoped<any>(`/v1/cost/services?${rangeParam}${regParamAmp}`),
        scoped<any>(`/v1/cost/trend?${rangeParam}${regParamAmp}`),
        scoped<any>(`/v1/cost/opportunities`),
        scoped<any>(drillUrl),
      ]);

      if (sumRes.status === 'fulfilled') setSummary(isAllAccounts ? mergeSummaries(sumRes.value as any[]) : sumRes.value);
      if (accRes.status === 'fulfilled') setAccountsCost(isAllAccounts ? mergeBreakdown(accRes.value as any[]) : (Array.isArray(accRes.value) ? accRes.value : (accRes.value ? [accRes.value] : [])));
      if (srvRes.status === 'fulfilled') {
        const val = srvRes.value;
        const list = isAllAccounts ? mergeBreakdown(val as any[], 'services') : (Array.isArray(val) ? val : (val?.services || []));
        setTopServices(list);
      }
      if (trdRes.status === 'fulfilled') setTrend(isAllAccounts ? mergeTrends(trdRes.value as any[]) : (Array.isArray(trdRes.value) ? trdRes.value : []));
      if (oppRes.status === 'fulfilled') setOpportunities(isAllAccounts ? (oppRes.value as any[]).flatMap((value) => value?.opportunities || []) : (Array.isArray(oppRes.value) ? oppRes.value : (oppRes.value?.opportunities || [])));
      if (drlRes.status === 'fulfilled') {
        if (isAllAccounts) {
          const payloads = drlRes.value as any[];
          setDrilldown({ ...(payloads[0] || {}), items: mergeBreakdown(payloads, 'items') });
        } else {
          setDrilldown(drlRes.value);
        }
      }
    } catch (err) {
      console.error('Failed to load cost intelligence:', err);
    } finally {
      setLoading(false);
    }
  }, [tenantId, region, timePeriod, customRange, isAllAccounts, workspaces, selectedService, selectedRegion]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!isConnected) {
    return (
      <div className="py-16 text-center text-gray-400 font-sans">
        Connect an AWS account to view cost intelligence.
      </div>
    );
  }

  const gross = summary?.gross ?? 0;
  const credits = summary?.adjustments ?? summary?.total_credits_and_discounts ?? summary?.credits ?? 0;
  const net = summary?.net ?? summary?.total_cost ?? 0;
  const prevPeriodNet = summary?.previous_period ?? summary?.previous_period_net ?? 0;
  const changePct = summary?.change_percent ?? 0;

  const totalSavings = opportunities.reduce((acc, o) => acc + (o.estimated_monthly_waste || o.potential_saving_monthly || 0), 0);
  const trendData = useMemo(() => trend.map((point) => ({
    ...point,
    ts: Date.parse(`${point.date}T00:00:00Z`),
  })).filter((point) => Number.isFinite(point.ts)), [trend]);

  return (
    <div className="space-y-8 font-sans">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white">Cost Intelligence</h1>
          <p className="text-sm text-gray-400 mt-0.5">{scopeLabel}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => void load()}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-800 bg-[#111827] text-gray-300 hover:text-white text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Financial totals returned by AWS Cost Explorer. */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Gross Spend</p>
          <p className="text-2xl font-bold text-white mt-2">{formatCurrency(gross)}</p>
          <p className="text-xs text-gray-500 mt-1">Usage before credits and refunds</p>
        </div>

        <div className="rounded-xl bg-[#111827] border border-gray-800 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Credits and Refunds</p>
          <p className="text-2xl font-bold text-emerald-400 mt-2">{credits === 0 ? formatCurrency(0) : `-${formatCurrency(Math.abs(credits))}`}</p>
          <p className="text-xs text-gray-500 mt-1">Signed AWS credits, refunds, and discounts</p>
        </div>

        <div className="rounded-xl bg-[#111827] border border-gray-800 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Net Out-of-Pocket</p>
          <p className="text-2xl font-bold text-white mt-2">{formatCurrency(net)}</p>
          <span className={`text-xs font-medium block mt-1 ${changePct >= 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
            Previous: {formatCurrency(prevPeriodNet)} ({Math.abs(changePct)}% shift)
          </span>
        </div>

        <div className="rounded-xl bg-[#111827] border border-gray-800 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Potential Savings</p>
          <p className="text-2xl font-bold text-emerald-400 mt-2">{formatCurrency(totalSavings)}/mo</p>
          <p className="text-xs text-emerald-500/80 mt-1">{opportunities.length} metric-backed opportunities</p>
        </div>
      </div>

      {/* Spend Trend Graph */}
      <div className="rounded-xl bg-[#111827] border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase">SPEND TREND</h2>
          <span className="text-xs text-gray-500 font-mono">{scopeLabel}</span>
        </div>

        {trend.length === 0 ? (
          <div className="h-32 flex items-center justify-center text-xs text-gray-500">
            No daily trend points recorded for this scope.
          </div>
        ) : (
          <div className="h-48 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <RLineChart data={trendData} syncId="cost-trend" margin={{ top: 5, right: 12, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis type="number" dataKey="ts" domain={['dataMin', 'dataMax']} tick={{ fill: '#6b7280', fontSize: 11 }} tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip content={<CostTrendTooltip scope={scopeLabel} region={region} />} />
                <Line type="monotone" dataKey="gross" name="Gross" stroke="#38bdf8" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="net" name="Net out-of-pocket" stroke="#10b981" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="forecast" name="Observed-period baseline" stroke="#f59e0b" strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                <Brush dataKey="ts" height={20} stroke="#374151" fill="#0B0F17" travellerWidth={8} tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
              </RLineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Grid: Cost by Account & Cost by Service */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost by Account */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-6">
          <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase mb-4">COST BY ACCOUNT</h2>
          {accountsCost.length === 0 ? (
            <p className="text-xs text-gray-500 py-4 text-center">No multi-account breakdown available.</p>
          ) : (
            <div className="space-y-3">
              {accountsCost.map((acc, idx) => (
                <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-800/60 last:border-0 text-sm">
                  <div>
                    <span className="font-medium text-white block">{acc.account_name || acc.aws_account_id}</span>
                    <span className="text-xs text-gray-500 font-mono">{acc.aws_account_id}</span>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-gray-200 block">{formatCurrency(acc.cost || 0)}</span>
                    <span className="text-xs text-emerald-400 font-mono">{acc.gross_percentage ?? acc.percentage ?? 0}% of gross</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cost by Service Table */}
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-6 lg:col-span-2 font-sans">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase">COST BY SERVICE</h2>
              <p className="text-xs text-gray-500 mt-0.5">Click a service to drill down into Account → Region → Resource</p>
            </div>
            <span className="text-xs text-gray-400 font-mono bg-gray-900 px-2 py-0.5 rounded border border-gray-800">
              {topServices.length} Services
            </span>
          </div>

          {topServices.length === 0 ? (
            <p className="text-xs text-gray-500 py-4 text-center">No service cost breakdown available for this scope.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 uppercase tracking-wider font-semibold">
                    <th className="pb-3">Service</th>
                    <th className="pb-3 text-right">Gross</th>
                    <th className="pb-3 text-right">Credits</th>
                    <th className="pb-3 text-right">Net Spend</th>
                    <th className="pb-3 text-right">% of Gross</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/80">
                  {topServices.map((srv, idx) => {
                    const sName = srv.service || srv.name;
                    const gVal = srv.gross ?? srv.cost ?? 0;
                    const cVal = srv.credits ?? 0;
                    const nVal = srv.net ?? srv.cost ?? 0;
                    const pct = srv.gross_percentage ?? srv.percentage ?? 0;
                    return (
                      <tr
                        key={idx}
                        onClick={() => setSelectedService(sName)}
                        className={`hover:bg-white/5 cursor-pointer transition-colors ${
                          selectedService === sName ? 'bg-emerald-600/10 text-emerald-400 font-semibold' : ''
                        }`}
                      >
                        <td className="py-3 font-semibold text-white flex items-center gap-1.5">
                          {sName}
                          <ChevronRight className="w-3 h-3 text-gray-500" />
                        </td>
                        <td className="py-3 text-right font-mono text-gray-300">{formatCurrency(gVal)}</td>
                        <td className="py-3 text-right font-mono text-emerald-400">
                          {cVal === 0 ? '$0.00' : `-${formatCurrency(Math.abs(cVal))}`}
                        </td>
                        <td className="py-3 text-right font-mono font-bold text-white">{formatCurrency(nVal)}</td>
                        <td className="py-3 text-right font-mono text-emerald-400 font-semibold">{pct}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Resource Cost Drill-Down */}
      <div className="rounded-xl bg-[#111827] border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase">RESOURCE COST DRILL-DOWN</h2>
            <p className="text-xs text-gray-500 mt-0.5">Service &rarr; Region &rarr; Resource. Resource totals appear only when AWS provides attribution.</p>
          </div>

          {selectedService && (
            <button
              onClick={() => {
                setSelectedService(null);
                setSelectedRegion(null);
              }}
              className="text-xs text-emerald-400 hover:underline"
            >
              Clear Drill-Down Filter
            </button>
          )}
        </div>

        {/* Breadcrumb Navigation */}
        <div className="flex items-center gap-2 text-xs font-medium mb-4 bg-[#0B0F17] p-2.5 rounded-lg border border-gray-800 text-gray-400">
          <span className={`cursor-pointer hover:text-white ${!selectedService ? 'text-emerald-400 font-semibold' : ''}`} onClick={() => { setSelectedService(null); setSelectedRegion(null); }}>
            Total ({formatCurrency(gross)})
          </span>
          {selectedService && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-gray-600" />
              <span className={`cursor-pointer hover:text-white ${!selectedRegion ? 'text-emerald-400 font-semibold' : ''}`} onClick={() => setSelectedRegion(null)}>
                {selectedService}
              </span>
            </>
          )}
          {selectedRegion && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-gray-600" />
              <span className="text-emerald-400 font-semibold">{selectedRegion}</span>
            </>
          )}
        </div>

        <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
          {drilldown?.items?.length === 0 && selectedRegion ? (
            <p className="py-6 text-center text-xs text-gray-500">{drilldown?.message || 'No data available from AWS Cost Explorer for this resource scope.'}</p>
          ) : drilldown?.items?.map((item: any, idx: number) => (
            <div
              key={idx}
              onClick={() => {
                if (item.level === 'SERVICE') {
                  setSelectedService(item.name);
                } else if (item.level === 'REGION') {
                  setSelectedRegion(item.name);
                }
              }}
              className="p-3 rounded-lg bg-[#0B0F17] border border-gray-800/80 hover:border-emerald-500/40 transition-all cursor-pointer flex justify-between items-center text-xs"
            >
              <div>
                <span className="font-semibold text-white flex items-center gap-1.5">
                  {item.name}
                  {item.level !== 'RESOURCE' && <ChevronRight className="w-3.5 h-3.5 text-gray-500" />}
                </span>
                <span className="text-[10px] font-mono text-gray-500 uppercase mt-0.5 block">
                  {item.level}{item.aws_account_id ? ` | ${item.aws_account_id}` : ''}
                </span>
              </div>
              <div className="text-right font-mono">
                <span className="font-semibold text-emerald-400 block">{formatCurrency(item.gross || item.cost || 0)}</span>
                <span className="text-[10px] text-gray-500 block">{item.percentage ?? 0}% of gross</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Savings Opportunities */}
      <div className="rounded-xl bg-[#111827] border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase">SAVINGS OPPORTUNITIES</h2>
          <span className="text-xs text-gray-400">{opportunities.length} opportunities identified</span>
        </div>

        {opportunities.length === 0 ? (
          <p className="text-xs text-gray-500 py-4 text-center">No optimization opportunities detected for this scope.</p>
        ) : (
          <div className="space-y-3">
            {opportunities.map((opp, idx) => (
              <div key={idx} className="p-3.5 rounded-lg bg-[#0B0F17] border border-gray-800 space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">{opp.title || opp.name}</span>
                  <span className="font-semibold text-emerald-400">
                    {formatCurrency(opp.estimated_monthly_waste || opp.potential_saving_monthly || 0)}/mo potential saving
                  </span>
                </div>
                <p className="text-gray-400">{opp.why || opp.recommendation}</p>
                <div className="flex items-center justify-between pt-1 text-[11px] text-gray-500">
                  <span>Resource: {opp.resource_id}</span>
                  <span className="font-mono text-emerald-500">Confidence: {opp.confidence || 'HIGH'}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        <p className="text-xs text-gray-500 mt-4 pt-3 border-t border-gray-800">
          *Costs & savings derived directly from AWS Cost Explorer & CloudWatch telemetry
        </p>
      </div>
    </div>
  );
}

function CostTrendTooltip({ active, payload, label, scope, region }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-gray-700 bg-[#111827] px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-300 font-medium">{label ? new Date(label).toISOString() : 'No timestamp'}</p>
      <p className="text-gray-500">Scope: {scope}</p>
      <p className="text-gray-500">Region: {region || 'All regions'} | Service: All services</p>
      {payload.map((entry: any) => <p key={entry.dataKey} style={{ color: entry.color }}>{entry.name}: {formatCurrency(Number(entry.value || 0))}</p>)}
    </div>
  );
}
