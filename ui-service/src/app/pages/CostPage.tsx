import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { DollarSign, Play, PlugZap, RefreshCw, TrendingDown, ShieldAlert } from 'lucide-react';
import { apiFetch, errorMessage } from '../lib/api';
import { formatCurrency } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { Insight } from '../lib/types';
import { EmptyState, ErrorBanner, Panel, Spinner, StatCard } from '../components/dashboard/primitives';

interface AsyncJobResponse {
  job_id?: string;
  status?: string;
  message?: string;
}

export function CostPage() {
  const navigate = useNavigate();
  const { tenantId, region, isConnected } = useTenant();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
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

  const runCostAnalysis = useCallback(async () => {
    if (!tenantId) return;
    setAnalyzing(true);
    setError('');
    try {
      const path = region
        ? `/v1/insights/${tenantId}/analyze?region=${encodeURIComponent(region)}`
        : `/v1/insights/${tenantId}/analyze`;
      const res = await apiFetch<AsyncJobResponse>(path, { method: 'POST', tenantId });
      if (res.job_id) {
        let attempts = 0;
        while (attempts < 15) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          attempts++;
          try {
            const jobStatus = await apiFetch<AsyncJobResponse>(`/v1/insights/jobs/${res.job_id}`, { tenantId });
            if (jobStatus.status === 'completed' || jobStatus.status === 'failed') break;
          } catch {
            break;
          }
        }
      }
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setAnalyzing(false);
    }
  }, [tenantId, region, load]);

  useEffect(() => {
    if (tenantId) {
      void load();
    }
  }, [tenantId, load]);

  const costInsights = useMemo(
    () =>
      insights.filter(
        (i) =>
          i.category === 'cost_optimization' ||
          i.category === 'cost' ||
          (i.estimated_monthly_waste || 0) > 0 ||
          (i.issue && i.issue.toLowerCase().includes('idle')) ||
          (i.issue && i.issue.toLowerCase().includes('cost'))
      ),
    [insights]
  );

  const totalSavings = useMemo(
    () => costInsights.reduce((s, i) => s + (i.estimated_monthly_waste || 0), 0),
    [costInsights]
  );
  const idleCount = useMemo(
    () => costInsights.filter((i) => i.issue?.toLowerCase().includes('idle')).length,
    [costInsights]
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
          <p className="text-gray-400 text-sm mt-1">Savings opportunities & right-sizing recommendations.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void load()}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-600 text-sm disabled:opacity-40"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => void runCostAnalysis()}
            disabled={analyzing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-40"
          >
            <Play className={`w-4 h-4 ${analyzing ? 'animate-pulse' : ''}`} />
            {analyzing ? 'Analyzing...' : 'Run Cost Analysis'}
          </button>
        </div>
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
          label="Annualized Savings"
          value={formatCurrency(totalSavings * 12)}
          accent={totalSavings > 0 ? 'text-emerald-400' : 'text-white'}
          hint="est. / year"
        />
      </div>

      {loading && costInsights.length === 0 ? (
        <Spinner label="Loading cost findings..." />
      ) : costInsights.length === 0 ? (
        <EmptyState
          icon={<TrendingDown className="w-10 h-10" />}
          title="No cost opportunities found"
          description="Click 'Run Cost Analysis' to analyze idle and underutilized resources across EC2, RDS, and Lambda."
          action={
            <button
              onClick={() => void runCostAnalysis()}
              disabled={analyzing}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
            >
              Run Cost Analysis
            </button>
          }
        />
      ) : (
        <Panel className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <th className="px-4 py-3 font-medium">Resource ID</th>
                  <th className="px-4 py-3 font-medium">Resource Type</th>
                  <th className="px-4 py-3 font-medium">Issue / Finding</th>
                  <th className="px-4 py-3 font-medium">Est. Monthly Waste</th>
                  <th className="px-4 py-3 font-medium">Actionable Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {costInsights.map((i) => (
                  <tr key={i.id} className="border-b border-gray-800/60 hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-white">{i.resource_id}</td>
                    <td className="px-4 py-3 text-gray-300 capitalize">{i.resource_type ?? i.instance_type ?? 'EC2'}</td>
                    <td className="px-4 py-3 text-gray-300">{i.issue || i.title}</td>
                    <td className="px-4 py-3 text-emerald-400 font-semibold">
                      {i.estimated_monthly_waste ? formatCurrency(i.estimated_monthly_waste) + '/mo' : '$0.00'}
                    </td>
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
        Estimates use live telemetry metrics & AWS instance pricing lookup.
      </p>
    </div>
  );
}
