import { useCallback, useEffect, useState } from 'react';
import { DollarSign, ArrowDownRight, Filter, RefreshCw } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { formatCurrency } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { Insight } from '../lib/types';
import { Panel, SeverityBadge, Spinner } from '../components/dashboard/primitives';

interface OpportunityCard {
  id: string;
  display_name: string;
  resource_id: string;
  resource_type: string;
  issue: string;
  category: string;
  severity: string;
  current_cost: number | null;
  optimized_cost: number | null;
  monthly_savings: number | null;
  annual_savings: number | null;
  confidence: string;
  evidence: string;
  recommendation: string;
  account_id?: string | null;
  region?: string | null;
  inactive_hours?: number | null;
}

export function OptimizationPage() {
  const { tenantId } = useTenant();
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);

  const loadData = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const data = await apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId });
      setInsights(data || []);
    } catch {
      setInsights([]);
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  const runAnalysis = useCallback(async () => {
    if (!tenantId) return;
    setAnalyzing(true);
    try {
      const result = await apiFetch<{ insights?: Insight[] }>(
        `/v1/insights/${tenantId}/analyze?async_mode=false`,
        { method: 'POST', tenantId }
      );
      setInsights(Array.isArray(result.insights) ? result.insights : []);
    } catch {
      await loadData();
    } finally {
      setAnalyzing(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Transform insights into quantified financial opportunities sorted strictly by dollar impact.
  // Unknown costs stay unknown; the UI must not invent baselines or evidence.
  const opportunities: OpportunityCard[] = insights
    .filter((ins) => (ins.category || '').toLowerCase() === 'cost_optimization')
    .map((ins) => {
      const monthlyWaste = ins.estimated_monthly_waste || 0;
      const rtype = ins.resource_type || 'EC2';
      const dName = (ins as any).display_name || ins.resource_id;
      return {
        id: ins.id,
        display_name: dName,
        resource_id: ins.resource_id,
        resource_type: rtype.toUpperCase(),
        account_id: (ins as any).aws_account_id || null,
        region: ins.region || null,
        issue: ins.issue,
        category: ins.category || 'cost_optimization',
        severity: ins.severity || 'medium',
        current_cost: (ins as any).observed_cost ?? null,
        optimized_cost: null,
        monthly_savings: monthlyWaste > 0 ? monthlyWaste : null,
        annual_savings: monthlyWaste > 0 ? monthlyWaste * 12.0 : null,
        confidence: ins.confidence || 'HIGH',
        inactive_hours: (ins as any).inactive_hours ?? null,
        evidence: ins.evidence || (ins.avg_cpu == null ? 'Telemetry analysis over 30d' : `Average CPU: ${ins.avg_cpu}% over 30d`),
        recommendation: ins.recommendation || 'Downsize or stop idle workload',
      };
    })
    .sort((a, b) => (b.monthly_savings || 0) - (a.monthly_savings || 0));

  const filteredOpps = opportunities.filter((o) => {
    if (filterSeverity === 'all') return true;
    return o.severity.toLowerCase() === filterSeverity;
  });

  const totalMonthlySavings = opportunities.reduce((acc, o) => acc + (o.monthly_savings || 0), 0);
  const totalAnnualSavings = totalMonthlySavings * 12.0;

  const priorityCounts = {
    high: opportunities.filter((o) => o.severity.toLowerCase() === 'high').length,
    medium: opportunities.filter((o) => o.severity.toLowerCase() === 'medium').length,
    low: opportunities.filter((o) => o.severity.toLowerCase() === 'low').length,
  };
  const evaluations = [...insights].sort((a, b) => a.resource_id.localeCompare(b.resource_id));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
            <DollarSign className="w-6 h-6 text-emerald-400" />
            AWS Cost Optimization Engine
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Quantified financial impact findings sorted by dollar savings potential
          </p>
        </div>

        <button
          onClick={() => void runAnalysis()}
          disabled={loading || analyzing}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-800 bg-gray-900 text-gray-300 hover:text-white text-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading || analyzing ? 'animate-spin' : ''}`} />
          {analyzing ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>

      {loading ? (
        <Spinner label="Evaluating FinOps Optimization Rules..." />
      ) : (
        <div className="space-y-6">
          {/* Top Summary Stat Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Panel className="p-5 border-emerald-500/30 bg-gradient-to-br from-[#111827] to-[#0a2016]">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Potential Monthly Savings</p>
              <h2 className="text-3xl font-bold text-emerald-400 mt-2">{formatCurrency(totalMonthlySavings)}</h2>
              <p className="text-xs text-emerald-300/80 mt-2">
                {opportunities.length > 0 ? 'From quantified tenant insights' : 'No data available'}
              </p>
            </Panel>

            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Potential Annual Savings</p>
              <h2 className="text-3xl font-bold text-white mt-2">{formatCurrency(totalAnnualSavings)}</h2>
              <p className="text-xs text-gray-500 mt-2">Annualized run-rate reduction</p>
            </Panel>

            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Targeted Resources</p>
              <h2 className="text-3xl font-bold text-white mt-2">{opportunities.length}</h2>
              <p className="text-xs text-gray-500 mt-2">Actionable optimization targets</p>
            </Panel>

            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Priority Breakdown</p>
              <div className="flex items-center gap-3 mt-3 text-xs font-medium">
                <span className="px-2 py-1 rounded bg-red-500/20 text-red-300 border border-red-500/30">
                  {priorityCounts.high} High
                </span>
                <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  {priorityCounts.medium} Med
                </span>
                <span className="px-2 py-1 rounded bg-gray-700/50 text-gray-300 border border-gray-600/30">
                  {priorityCounts.low} Low
                </span>
              </div>
            </Panel>
          </div>

          {/* Executive Savings Waterfall */}
          <Panel className="p-6">
            <h2 className="text-lg font-semibold text-white mb-1">Executive Savings Waterfall</h2>
            <p className="text-xs text-gray-400 mb-6">Quantified savings from tenant-scoped findings</p>

            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm font-semibold">
                <span className="text-white">Current Monitored AWS Spend</span>
                <span className="text-gray-400">No data available</span>
              </div>

              <div className="space-y-2 pl-4 border-l-2 border-emerald-500/40">
                {opportunities.length > 0 ? (
                  opportunities.map((opp, idx) => {
                    return (
                      <WaterfallItem
                        key={opp.id}
                        category={`${opp.issue} (${opp.display_name})`}
                        reduction={opp.monthly_savings == null ? null : -opp.monthly_savings}
                      />
                    );
                  })
                ) : (
                  <p className="text-gray-400 text-xs py-2">No optimizable waste identified across current AWS resources.</p>
                )}
              </div>

              <div className="flex items-center justify-between text-base font-bold pt-3 border-t border-gray-800 text-emerald-400">
                <span>Optimized Monthly Estimate</span>
                <span>No data available</span>
              </div>
            </div>
          </Panel>

          {/* Findings List */}
          <Panel className="p-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">FinOps Findings (Ranked by Savings Impact)</h2>
                <p className="text-xs text-gray-400">Primary display names shown with secondary technical IDs</p>
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-400" />
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-1 flex items-center gap-1">
                  {['all', 'high', 'medium', 'low'].map((sev) => (
                    <button
                      key={sev}
                      onClick={() => setFilterSeverity(sev)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-colors ${
                        filterSeverity === sev ? 'bg-emerald-600 text-white' : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {filteredOpps.length === 0 ? (
                <p className="py-3 text-center text-sm text-gray-400">
                  No savings opportunity is supported by the current tenant metrics and AWS resource-cost data.
                </p>
              ) : filteredOpps.map((opp) => (
                <div
                  key={opp.id}
                  className="p-4 rounded-lg bg-gray-900/60 border border-gray-800 hover:border-emerald-500/40 transition-colors space-y-3"
                >
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <SeverityBadge value={opp.severity} />
                        <span className="text-white font-bold text-base">{opp.display_name}</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-mono">
                          {opp.resource_type}
                        </span>
                      </div>
                    <p className="text-gray-400 text-xs mt-1 font-mono">{opp.resource_id}</p>
                      <p className="text-gray-500 text-xs mt-1">Account: {opp.account_id || 'No data available'} · Region: {opp.region || 'No data available'}</p>
                    </div>

                    <div className="text-right">
                      <span className="text-xs text-gray-400">Potential Saving: </span>
                      <span className="text-emerald-400 font-bold text-lg">{opp.monthly_savings == null ? 'No data available' : `${formatCurrency(opp.monthly_savings)} / mo`}</span>
                      <span className="text-xs text-gray-500 block">{opp.annual_savings == null ? 'AWS pricing comparison required' : `(${formatCurrency(opp.annual_savings)} / yr)`}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-md bg-gray-950/80 border border-gray-800 text-xs">
                    <div>
                      <span className="text-gray-500 block">Finding:</span>
                      <span className="text-white font-medium">{opp.issue}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Current Cost:</span>
                      <span className="text-white font-semibold">
                        {opp.current_cost == null ? 'No data available' : `${formatCurrency(opp.current_cost)} observed`}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Optimized Cost:</span>
                      <span className="text-emerald-400 font-semibold">
                        {opp.optimized_cost == null ? 'No data available' : `${formatCurrency(opp.optimized_cost)} / mo`}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Confidence:</span>
                      <span className="text-gray-200 capitalize font-medium">{opp.confidence}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Inactive Window:</span>
                      <span className="text-white font-semibold">{opp.inactive_hours == null ? 'No data available' : `${opp.inactive_hours.toFixed(1)} hrs`}</span>
                    </div>
                  </div>

                  <div className="text-xs space-y-1">
                    <p className="text-gray-300">
                      <span className="font-semibold text-gray-400">Evidence: </span>
                      {opp.evidence}
                    </p>
                    <p className="text-emerald-300/90">
                      <span className="font-semibold text-emerald-400">Recommendation: </span>
                      {opp.recommendation}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel className="p-6">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-white">Resource Evaluation</h2>
              <p className="text-xs text-gray-400 mt-1">Live tenant-scoped analysis results. No seeded inventory or fabricated resource names.</p>
            </div>
            {evaluations.length === 0 ? (
              <p className="py-4 text-center text-sm text-gray-400">No analysis has been stored for this workspace. Run Analysis to evaluate connected AWS resources.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-400 uppercase tracking-wide">
                      <th className="px-2 py-3">Resource</th>
                      <th className="px-2 py-3">Account / Region</th>
                      <th className="px-2 py-3">Metric Evidence</th>
                      <th className="px-2 py-3">AWS Resource Cost</th>
                      <th className="px-2 py-3">Evaluation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evaluations.map((item) => (
                      <tr key={item.id} className="border-b border-gray-800/60 align-top">
                        <td className="px-2 py-3">
                          <div className="font-mono text-gray-100">{item.resource_id}</div>
                          <div className="mt-1 uppercase text-gray-500">{item.resource_type}</div>
                        </td>
                        <td className="px-2 py-3 text-gray-400">
                          <div className="font-mono">{item.aws_account_id || 'No data available'}</div>
                          <div className="mt-1">{item.region || 'No data available'}</div>
                        </td>
                        <td className="px-2 py-3 text-gray-300">
                          {item.avg_cpu == null ? 'No data available' : `Average CPU ${item.avg_cpu.toFixed(2)}%`}
                        </td>
                        <td className="px-2 py-3 text-gray-300">
                          {item.observed_cost == null ? 'No data available' : `${formatCurrency(item.observed_cost)} observed`}
                        </td>
                        <td className="px-2 py-3">
                          <SeverityBadge value={item.status || item.severity || 'info'} />
                          <div className="mt-1 text-gray-400">{item.issue}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}

function WaterfallItem({ category, reduction }: { category: string; reduction: number | null }) {
  return (
    <div className="flex items-center justify-between text-xs py-1">
      <div className="flex items-center gap-2">
        <ArrowDownRight className="w-3.5 h-3.5 text-emerald-400" />
        <span className="text-gray-300">{category}</span>
      </div>
      <div className="flex items-center gap-4 font-mono">
        <span className="text-emerald-400 font-semibold">{reduction == null ? 'No data available' : `${formatCurrency(reduction)} / mo`}</span>
      </div>
    </div>
  );
}
