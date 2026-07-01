import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Bell, PlugZap, RefreshCw } from 'lucide-react';
import { apiFetch, errorMessage } from '../lib/api';
import { formatDateTime } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { Insight } from '../lib/types';
import {
  EmptyState,
  ErrorBanner,
  Panel,
  SeverityBadge,
  Spinner,
} from '../components/dashboard/primitives';

// Alerts are derived from Insight Engine findings. There's no alert backend yet,
// so the Open/Acknowledged/Resolved status is tracked client-side (localStorage)
// keyed by tenant + finding id — ready to swap for a real status API later.

type Status = 'open' | 'acknowledged' | 'resolved';
const STATUSES: Status[] = ['open', 'acknowledged', 'resolved'];

function statusKey(tenantId: string) {
  return `devops-copilot.alertStatus.${tenantId}`;
}
function loadStatuses(tenantId: string): Record<string, Status> {
  try {
    return JSON.parse(localStorage.getItem(statusKey(tenantId)) || '{}');
  } catch {
    return {};
  }
}

export function AlertsPage() {
  const navigate = useNavigate();
  const { tenantId, isConnected } = useTenant();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [statuses, setStatuses] = useState<Record<string, Status>>({});
  const [filter, setFilter] = useState<Status | 'all'>('all');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setError('');
    try {
      setInsights(await apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId }));
      setStatuses(loadStatuses(tenantId));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const setStatus = useCallback(
    (id: string, status: Status) => {
      setStatuses((prev) => {
        const next = { ...prev, [id]: status };
        try {
          localStorage.setItem(statusKey(tenantId), JSON.stringify(next));
        } catch {
          /* ignore */
        }
        return next;
      });
    },
    [tenantId]
  );

  const alerts = useMemo(
    () =>
      insights.map((i) => ({
        insight: i,
        status: statuses[i.id] ?? ('open' as Status),
      })),
    [insights, statuses]
  );

  const filtered = useMemo(
    () => (filter === 'all' ? alerts : alerts.filter((a) => a.status === filter)),
    [alerts, filter]
  );

  const counts = useMemo(() => {
    const c: Record<Status, number> = { open: 0, acknowledged: 0, resolved: 0 };
    alerts.forEach((a) => (c[a.status] += 1));
    return c;
  }, [alerts]);

  if (!isConnected) {
    return (
      <EmptyState
        icon={<PlugZap className="w-10 h-10" />}
        title="No AWS account connected"
        description="Connect an AWS account to receive alerts."
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
          <h1 className="text-2xl font-semibold text-white">Alerts</h1>
          <p className="text-gray-400 text-sm mt-1">Findings that require attention, from analysis.</p>
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

      {/* Status filter */}
      <div className="flex gap-2 mb-5">
        {(['all', ...STATUSES] as const).map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm border capitalize ${
              filter === s
                ? 'border-emerald-500 text-white bg-emerald-600/10'
                : 'border-gray-700 text-gray-400 hover:text-white'
            }`}
          >
            {s}
            {s !== 'all' && <span className="text-gray-500"> ({counts[s as Status]})</span>}
          </button>
        ))}
      </div>

      {loading && insights.length === 0 ? (
        <Spinner label="Loading alerts…" />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Bell className="w-10 h-10" />}
          title={alerts.length === 0 ? 'No alerts' : 'Nothing in this status'}
          description={
            alerts.length === 0
              ? 'Alerts appear here when analysis surfaces issues. Run an analysis from the Insights page.'
              : undefined
          }
        />
      ) : (
        <Panel className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-800">
                  <th className="px-4 py-3 font-medium">Severity</th>
                  <th className="px-4 py-3 font-medium">Resource</th>
                  <th className="px-4 py-3 font-medium">Message</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(({ insight: i, status }) => (
                  <tr key={i.id} className="border-b border-gray-800/60 hover:bg-white/[0.02]">
                    <td className="px-4 py-3"><SeverityBadge value={i.severity} /></td>
                    <td className="px-4 py-3 font-mono text-xs text-white">{i.resource_id}</td>
                    <td className="px-4 py-3 text-gray-300">{i.issue}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDateTime(i.created_at)}</td>
                    <td className="px-4 py-3"><SeverityBadge value={status} /></td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {status !== 'acknowledged' && status !== 'resolved' && (
                        <button
                          onClick={() => setStatus(i.id, 'acknowledged')}
                          className="text-xs text-amber-400 hover:text-amber-300 mr-3"
                        >
                          Acknowledge
                        </button>
                      )}
                      {status !== 'resolved' ? (
                        <button
                          onClick={() => setStatus(i.id, 'resolved')}
                          className="text-xs text-emerald-400 hover:text-emerald-300"
                        >
                          Resolve
                        </button>
                      ) : (
                        <button
                          onClick={() => setStatus(i.id, 'open')}
                          className="text-xs text-gray-400 hover:text-white"
                        >
                          Reopen
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
