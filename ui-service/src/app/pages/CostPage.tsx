import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { DollarSign, PlugZap, RefreshCw, TrendingDown } from 'lucide-react';
import { apiFetch, errorMessage } from '../lib/api';
import { formatCurrency } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { Insight } from '../lib/types';
import { EmptyState, ErrorBanner, Panel, Spinner, StatCard } from '../components/dashboard/primitives';

// Cost intelligence sourced from Insight Engine findings (no Cost Explorer yet).
export function CostPage() {
  const navigate = useNavigate();
  const { tenantId, isConnected } = useTenant();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setError('');
    try {
      setInsights(await apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const costInsights = useMemo(
    () => insights.filter((i) => (i.estimated_monthly_waste || 0) > 0),
    [insights]
  );
  const totalSavings = useMemo(
    () => costInsights.reduce((s, i) => s + (i.estimated_monthly_waste || 0), 0),
    [costInsights]
  );
  const idleCount = useMemo(
    () => insights.filter((i) => i.category === 'cost_optimization').length,
    [insights]
  );

  if (!isConnected) {
    return (
      <EmptyState
        icon={<PlugZap className="w-10 h-10" />}
        title="No AWS account connected"
        description="Connect an AWS account to analyze cost."
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
      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Cost Optimization</h1>
          <p className="text-gray-400 text-sm mt-1">Savings opportunities from infrastructure analysis.</p>
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

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Potential Savings"
          value={formatCurrency(totalSavings)}
          accent={totalSavings > 0 ? 'text-emerald-400' : 'text-white'}
          hint="per month"
        />
        <StatCard label="Idle Resources" value={idleCount} />
        <StatCard label="Opportunities" value={costInsights.length} />
        <StatCard
          label="Annualized"
          value={formatCurrency(totalSavings * 12)}
          accent={totalSavings > 0 ? 'text-emerald-400' : 'text-white'}
          hint="est. / year"
        />
      </div>

      {loading && insights.length === 0 ? (
        <Spinner label="Loading cost findings…" />
      ) : costInsights.length === 0 ? (
        <EmptyState
          icon={<TrendingDown className="w-10 h-10" />}
          title="No cost opportunities found"
          description="Run an analysis from the Insights page to surface idle and underutilized resources."
        />
      ) : (
        <Panel className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <th className="px-4 py-3 font-medium">Resource</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Monthly Cost</th>
                  <th className="px-4 py-3 font-medium">Estimated Waste</th>
                  <th className="px-4 py-3 font-medium">Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {costInsights.map((i) => (
                  <tr key={i.id} className="border-b border-gray-800/60 hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-white">{i.resource_id}</td>
                    <td className="px-4 py-3 text-gray-300">{i.instance_type ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-300">{formatCurrency(i.estimated_monthly_waste)}</td>
                    <td className="px-4 py-3 text-emerald-400">{formatCurrency(i.estimated_monthly_waste)}/mo</td>
                    <td className="px-4 py-3 text-gray-400">{i.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      <p className="text-gray-600 text-xs mt-4 flex items-center gap-1">
        <DollarSign className="w-3.5 h-3.5" />
        Estimates use a static instance price table. AWS Cost Explorer, Savings Plans and Reserved
        Instances are planned but not yet integrated.
      </p>
    </div>
  );
}
