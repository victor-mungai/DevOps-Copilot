import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Play, RefreshCw, Lightbulb, PlugZap } from 'lucide-react';
import { apiFetch, errorMessage } from '../lib/api';
import { formatCurrency, formatDateTime } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { AnalyzeResponse, Insight } from '../lib/types';
import {
  EmptyState,
  ErrorBanner,
  Panel,
  SeverityBadge,
  Spinner,
} from '../components/dashboard/primitives';

const ALL = 'all';

interface AsyncJobResponse {
  job_id?: string;
  status?: string;
  message?: string;
  insights_found?: number;
}

export function InsightsPage() {
  const navigate = useNavigate();
  const { tenantId, region, isConnected } = useTenant();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');

  const [severity, setSeverity] = useState(ALL);
  const [category, setCategory] = useState(ALL);
  const [resourceType, setResourceType] = useState(ALL);

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setError('');
    try {
      const rows = await apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId });
      setInsights(rows);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const runAnalysis = useCallback(async () => {
    if (!tenantId) return;
    setAnalyzing(true);
    setError('');
    try {
      const analyzePath = region ? `/v1/insights/${tenantId}/analyze?region=${encodeURIComponent(region)}` : `/v1/insights/${tenantId}/analyze`;
      const res = await apiFetch<AsyncJobResponse>(analyzePath, {
        method: 'POST',
        tenantId,
      });

      if (res.job_id) {
        let attempts = 0;
        while (attempts < 15) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          attempts++;
          try {
            const jobStatus = await apiFetch<AsyncJobResponse>(`/v1/insights/jobs/${res.job_id}`, { tenantId });
            if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
              break;
            }
          } catch (_) {
            break;
          }
        }
      }

      // Re-load the full persisted list so the table reflects everything stored.
      const rows = await apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId });
      setInsights(rows);
      if (rows.length === 0) {
        setError('Analysis completed but found no issues (no idle resources, or no metrics collected yet).');
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setAnalyzing(false);
    }
  }, [tenantId, region]);

  const categories = useMemo(
    () => Array.from(new Set(insights.map((i) => i.category).filter(Boolean))),
    [insights]
  );
  const resourceTypes = useMemo(
    () => Array.from(new Set(insights.map((i) => i.resource_type).filter(Boolean))),
    [insights]
  );

  const filtered = useMemo(
    () =>
      insights.filter(
        (i) =>
          (severity === ALL || i.severity?.toLowerCase() === severity) &&
          (category === ALL || i.category === category) &&
          (resourceType === ALL || i.resource_type === resourceType)
      ),
    [insights, severity, category, resourceType]
  );

  if (!isConnected) {
    return (
      <EmptyState
        icon={<PlugZap className="w-10 h-10" />}
        title="No AWS account connected"
        description="Connect an AWS account before generating insights."
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
          <h1 className="text-2xl font-semibold text-white">Insights Center</h1>
          <p className="text-gray-400 text-sm mt-1">
            Cost, performance and reliability findings for your environment.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => void load()}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-600 text-sm disabled:opacity-40"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => void runAnalysis()}
            disabled={analyzing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-medium"
          >
            <Play className={`w-4 h-4 ${analyzing ? 'animate-pulse' : ''}`} />
            {analyzing ? 'Analyzing…' : 'Run analysis'}
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <FilterSelect label="Severity" value={severity} onChange={setSeverity} options={['high', 'medium', 'low']} />
        <FilterSelect label="Category" value={category} onChange={setCategory} options={categories} />
        <FilterSelect label="Resource" value={resourceType} onChange={setResourceType} options={resourceTypes} />
      </div>

      {loading && insights.length === 0 ? (
        <Spinner label="Loading insights…" />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Lightbulb className="w-10 h-10" />}
          title={insights.length === 0 ? 'No insights yet' : 'No insights match these filters'}
          description={
            insights.length === 0
              ? 'Run an analysis to scan this account for cost-optimization and performance issues.'
              : 'Try clearing one of the filters above.'
          }
        />
      ) : (
        <Panel className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <Th>Severity</Th>
                  <Th>Category</Th>
                  <Th>Resource</Th>
                  <Th>Issue</Th>
                  <Th>Recommendation</Th>
                  <Th>Est. Waste</Th>
                  <Th>Created</Th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((i) => (
                  <tr key={i.id} className="border-b border-gray-800/60 hover:bg-white/[0.02]">
                    <Td><SeverityBadge value={i.severity} /></Td>
                    <Td className="text-gray-300">{i.category}</Td>
                    <Td>
                      <span className="text-white">{i.resource_id}</span>
                      {i.instance_type && <span className="text-gray-500"> · {i.instance_type}</span>}
                    </Td>
                    <Td className="text-gray-300">{i.issue}</Td>
                    <Td className="text-gray-400 max-w-xs">{i.recommendation}</Td>
                    <Td className="text-emerald-400 whitespace-nowrap">
                      {formatCurrency(i.estimated_monthly_waste)}/mo
                    </Td>
                    <Td className="text-gray-500 whitespace-nowrap">{formatDateTime(i.created_at)}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 text-xs text-gray-500 border-t border-gray-800">
            Showing {filtered.length} of {insights.length} insights
          </div>
        </Panel>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-gray-400">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-[#0B0F17] border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
      >
        <option value={ALL}>All</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-4 py-3 font-medium whitespace-nowrap">{children}</th>;
}
function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-3 align-top ${className}`}>{children}</td>;
}
