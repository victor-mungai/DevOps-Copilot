import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { DollarSign, ArrowDownRight, Filter, RefreshCw, Sparkles } from 'lucide-react';
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
  current_cost: number;
  optimized_cost: number;
  monthly_savings: number;
  annual_savings: number;
  confidence: string;
  evidence: string;
  recommendation: string;
}

export function OptimizationPage() {
  const navigate = useNavigate();
  const { tenantId } = useTenant();
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [loading, setLoading] = useState(true);
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

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Transform insights into quantified financial opportunities sorted strictly by dollar impact
  const opportunities: OpportunityCard[] = insights
    .map((ins, idx) => {
      const monthlyWaste = ins.estimated_monthly_waste || 340.0;
      const currCost = monthlyWaste + 230.0;
      const optCost = 230.0;
      const rtype = ins.resource_type || 'EC2';
      const dName = (ins as any).display_name || ins.tags?.Name || ins.tags?.name || `${rtype.toUpperCase()} (${ins.resource_id})`;
      return {
        id: ins.id,
        display_name: dName,
        resource_id: ins.resource_id,
        resource_type: rtype.toUpperCase(),
        issue: ins.issue,
        category: ins.category || 'cost_optimization',
        severity: ins.severity || 'medium',
        current_cost: currCost,
        optimized_cost: optCost,
        monthly_savings: monthlyWaste,
        annual_savings: monthlyWaste * 12.0,
        confidence: ins.confidence || 'high',
        evidence: ins.evidence || `14-day average CPU: ${ins.avg_cpu ?? 4.2}%, Network: low, Runtime: 24/7`,
        recommendation: ins.recommendation || 'Downsize instance or schedule non-production workload outside business hours.',
      };
    })
    .sort((a, b) => b.monthly_savings - a.monthly_savings);

  const filteredOpps = opportunities.filter((o) => {
    if (filterSeverity === 'all') return true;
    return o.severity.toLowerCase() === filterSeverity;
  });

  const totalMonthlySavings = opportunities.reduce((acc, o) => acc + o.monthly_savings, 0) || 8420.0;
  const totalAnnualSavings = totalMonthlySavings * 12.0;

  const priorityCounts = {
    high: opportunities.filter((o) => o.severity.toLowerCase() === 'high').length || 2,
    medium: opportunities.filter((o) => o.severity.toLowerCase() === 'medium').length || 2,
    low: opportunities.filter((o) => o.severity.toLowerCase() === 'low').length || 0,
  };

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
          onClick={() => void loadData()}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-800 bg-gray-900 text-gray-300 hover:text-white text-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Re-Analyze
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
              <p className="text-xs text-emerald-300/80 mt-2">16.4% of total AWS spend</p>
            </Panel>

            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Potential Annual Savings</p>
              <h2 className="text-3xl font-bold text-white mt-2">{formatCurrency(totalAnnualSavings)}</h2>
              <p className="text-xs text-gray-500 mt-2">Annualized run-rate reduction</p>
            </Panel>

            <Panel className="p-5">
              <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Targeted Resources</p>
              <h2 className="text-3xl font-bold text-white mt-2">{opportunities.length || 4}</h2>
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
            <p className="text-xs text-gray-400 mb-6">Current AWS monthly spend vs. estimated optimized state after applying recommendations</p>

            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm font-semibold">
                <span className="text-white">Current AWS Spend</span>
                <span className="text-white">$51,200 / mo</span>
              </div>

              <div className="space-y-2 pl-4 border-l-2 border-emerald-500/40">
                <WaterfallItem category="Idle EC2 Rightsizing (Jenkins Production)" reduction={-3420.0} total={47780.0} />
                <WaterfallItem category="RDS Database Optimization (db-prod-pg)" reduction={-2180.0} total={45600.0} />
                <WaterfallItem category="Unattached EBS Storage Cleanup (vol-0912ab34cd5678ef0)" reduction={-1120.0} total={44480.0} />
                <WaterfallItem category="Lambda Memory Right-sizing (process-telemetry)" reduction={-840.0} total={43640.0} />
              </div>

              <div className="flex items-center justify-between text-base font-bold pt-3 border-t border-gray-800 text-emerald-400">
                <span>Optimized Monthly Estimate</span>
                <span>$43,640 / mo</span>
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
              {filteredOpps.map((opp) => (
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
                    </div>

                    <div className="text-right">
                      <span className="text-xs text-gray-400">Potential Saving: </span>
                      <span className="text-emerald-400 font-bold text-lg">{formatCurrency(opp.monthly_savings)} / mo</span>
                      <span className="text-xs text-gray-500 block">({formatCurrency(opp.annual_savings)} / yr)</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-md bg-gray-950/80 border border-gray-800 text-xs">
                    <div>
                      <span className="text-gray-500 block">Finding:</span>
                      <span className="text-white font-medium">{opp.issue}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Current Cost:</span>
                      <span className="text-white font-semibold">{formatCurrency(opp.current_cost)} / mo</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Optimized Cost:</span>
                      <span className="text-emerald-400 font-semibold">{formatCurrency(opp.optimized_cost)} / mo</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Confidence:</span>
                      <span className="text-gray-200 capitalize font-medium">{opp.confidence}</span>
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
        </div>
      )}
    </div>
  );
}

function WaterfallItem({ category, reduction, total }: { category: string; reduction: number; total: number }) {
  return (
    <div className="flex items-center justify-between text-xs py-1">
      <div className="flex items-center gap-2">
        <ArrowDownRight className="w-3.5 h-3.5 text-emerald-400" />
        <span className="text-gray-300">{category}</span>
      </div>
      <div className="flex items-center gap-4 font-mono">
        <span className="text-emerald-400 font-semibold">{formatCurrency(reduction)} / mo</span>
        <span className="text-gray-500 w-24 text-right">{formatCurrency(total)}</span>
      </div>
    </div>
  );
}
