import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Play, RefreshCw, Bot, Server } from 'lucide-react';
import { apiFetch, errorMessage } from '../lib/api';
import { formatCurrency } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { Insight } from '../lib/types';
import { ErrorBanner, Spinner } from '../components/dashboard/primitives';

type FilterSev = 'all' | 'critical' | 'high' | 'medium';

export function InsightsPage() {
  const navigate = useNavigate();
  const { tenantId, region, isConnected } = useTenant();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');

  const [severityFilter, setSeverityFilter] = useState<FilterSev>('all');

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

  const runAnalysis = useCallback(async () => {
    if (!tenantId) return;
    setAnalyzing(true);
    setError('');
    try {
      const analyzePath = region ? `/v1/insights/${tenantId}/analyze?region=${encodeURIComponent(region)}` : `/v1/insights/${tenantId}/analyze`;
      await apiFetch<any>(analyzePath, {
        method: 'POST',
        tenantId,
      });

      // Poll until done or reload
      const rows = await apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId });
      setInsights(rows);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setAnalyzing(false);
    }
  }, [tenantId, region]);

  useEffect(() => {
    if (tenantId) {
      void load();
    }
  }, [tenantId, region, load]);

  const filtered = useMemo(
    () =>
      insights.filter(
        (i) => severityFilter === 'all' || i.severity?.toLowerCase() === severityFilter
      ),
    [insights, severityFilter]
  );

  if (!isConnected) {
    return (
      <div className="py-16 text-center text-gray-400 font-sans">
        Connect an AWS account to view insights and active findings.
      </div>
    );
  }

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Insights</h1>
          <p className="text-sm text-gray-400 mt-0.5">{insights.length} active findings</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => void load()}
            disabled={loading}
            className="p-2 rounded-lg border border-gray-800 text-gray-400 hover:text-white hover:border-gray-700 disabled:opacity-40"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => void runAnalysis()}
            disabled={analyzing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-40"
          >
            <Play className={`w-3.5 h-3.5 ${analyzing ? 'animate-pulse' : ''}`} />
            {analyzing ? 'Analyzing…' : 'Run analysis'}
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Severity Filter Tabs */}
      <div className="flex gap-2">
        {(['all', 'critical', 'high', 'medium'] as FilterSev[]).map((s) => (
          <button
            key={s}
            onClick={() => setSeverityFilter(s)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ${
              severityFilter === s
                ? 'bg-emerald-600/15 text-emerald-400 border border-emerald-600/30'
                : 'bg-[#111827] text-gray-400 hover:text-white border border-gray-800'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {loading && insights.length === 0 ? (
        <div className="py-12 flex justify-center">
          <Spinner label="Loading findings…" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-8 rounded-xl bg-[#111827] border border-gray-800 text-center text-gray-400 text-sm">
          No active findings match the selected severity.
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((item) => (
            <FindingCard key={item.id} item={item} onAskCopilot={() => navigate(`/copilot?prompt=${encodeURIComponent(item.title || item.issue)}`)} />
          ))}
        </div>
      )}
    </div>
  );
}

function FindingCard({ item, onAskCopilot }: { item: Insight; onAskCopilot: () => void }) {
  const navigate = useNavigate();
  const sev = (item.severity || 'medium').toUpperCase();

  const badgeStyle =
    sev === 'CRITICAL' || sev === 'HIGH'
      ? 'text-red-400 bg-red-500/10 border-red-500/20'
      : sev === 'MEDIUM'
      ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      : 'text-gray-300 bg-gray-800 border-gray-700';

  return (
    <div className="rounded-xl bg-[#111827] border border-gray-800 p-6 space-y-4">
      {/* Severity Badge & Title */}
      <div>
        <span className={`inline-block px-2.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border mb-2 ${badgeStyle}`}>
          {sev}
        </span>
        <h2 className="text-base font-semibold text-white">{item.title || item.issue}</h2>
      </div>

      {/* Resource Context */}
      <div className="bg-[#0B0F17] rounded-lg border border-gray-800/80 p-3.5 text-xs space-y-1">
        <div className="flex items-center justify-between text-gray-300 font-medium">
          <span>{item.resource_id}</span>
          {item.instance_type && <span className="font-mono text-gray-400">{item.instance_type}</span>}
        </div>
        {typeof item.avg_cpu === 'number' && (
          <p className="text-gray-500">CPU average: {item.avg_cpu}%</p>
        )}
      </div>

      {/* 3 Core Operational Answers: What happened? Why does it matter? What should I do? */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1 text-xs">
        <div>
          <span className="font-semibold text-gray-400 block uppercase tracking-wider text-[10px] mb-1">What happened?</span>
          <p className="text-gray-300">{item.issue}</p>
        </div>
        <div>
          <span className="font-semibold text-gray-400 block uppercase tracking-wider text-[10px] mb-1">Why does it matter?</span>
          <p className="text-gray-300">
            {item.estimated_monthly_waste > 0
              ? `Potential waste of ${formatCurrency(item.estimated_monthly_waste)}/mo in unoptimized AWS spend.`
              : 'Presents governance, reliability or compliance risk.'}
          </p>
        </div>
        <div>
          <span className="font-semibold text-gray-400 block uppercase tracking-wider text-[10px] mb-1">What should I do?</span>
          <p className="text-gray-300">{item.recommendation}</p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="pt-2 flex items-center gap-3 border-t border-gray-800">
        <button
          onClick={() => navigate('/infrastructure')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium"
        >
          <Server className="w-3.5 h-3.5" />
          View resource
        </button>
        <button
          onClick={onAskCopilot}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium"
        >
          <Bot className="w-3.5 h-3.5" />
          Ask Copilot
        </button>
      </div>
    </div>
  );
}
