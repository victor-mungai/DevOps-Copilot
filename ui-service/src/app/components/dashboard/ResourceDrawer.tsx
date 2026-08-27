import { useNavigate } from 'react-router';
import { X, Bot, Lightbulb, Info, Activity } from 'lucide-react';
import type { Insight } from '../../lib/types';
import { formatCurrency } from '../../lib/format';
import { SeverityBadge } from './primitives';

export interface DrawerResource {
  kind: 'EC2' | 'RDS' | 'Lambda';
  resourceId: string;
  title: string;
  meta: Record<string, string>;
}

// Slide-over detail panel: metadata + insights + AI entry point for a resource.
export function ResourceDrawer({
  resource,
  insights,
  onClose,
}: {
  resource: DrawerResource | null;
  insights: Insight[];
  onClose: () => void;
}) {
  const navigate = useNavigate();
  if (!resource) return null;

  const related = insights.filter((i) => i.resource_id === resource.resourceId);

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-30" onClick={onClose} />
      <aside className="fixed top-0 right-0 h-full w-full max-w-md bg-[#0f1623] border-l border-gray-800 z-40 flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <div className="min-w-0">
            <p className="text-xs text-emerald-400">{resource.kind}</p>
            <h2 className="text-white font-medium truncate">{resource.title}</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Metadata */}
          <Section icon={<Info className="w-4 h-4" />} title="Resource Metadata">
            <dl className="rounded-lg border border-gray-800 divide-y divide-gray-800">
              {Object.entries(resource.meta).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between px-3 py-2 text-sm">
                  <dt className="text-gray-400">{k}</dt>
                  <dd className="text-white font-mono text-xs truncate max-w-[60%]">{v || '—'}</dd>
                </div>
              ))}
            </dl>
          </Section>

          {/* Metrics */}
          <Section icon={<Activity className="w-4 h-4" />} title="Metrics">
            {related.find((i) => typeof i.avg_cpu === 'number') ? (
              <p className="text-sm text-gray-300">
                Avg CPU{' '}
                <span className="text-white font-medium">
                  {related.find((i) => typeof i.avg_cpu === 'number')?.avg_cpu}%
                </span>{' '}
                over the analysis window.
              </p>
            ) : (
              <p className="text-sm text-gray-500">
                Time-series charts arrive with the Metrics Explorer (Prometheus proxy).
              </p>
            )}
          </Section>

          {/* Insights */}
          <Section icon={<Lightbulb className="w-4 h-4" />} title={`Insights (${related.length})`}>
            {related.length === 0 ? (
              <p className="text-sm text-gray-500">No insights for this resource.</p>
            ) : (
              <div className="space-y-2">
                {related.map((i) => (
                  <div key={i.id} className="rounded-lg border border-gray-800 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <SeverityBadge value={i.severity} />
                      <span className="text-white text-sm">{i.issue}</span>
                    </div>
                    <p className="text-gray-400 text-xs">{i.recommendation}</p>
                    {i.estimated_monthly_waste > 0 && (
                      <p className="text-emerald-400 text-xs mt-1">
                        {formatCurrency(i.estimated_monthly_waste)}/mo potential savings
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>

        <div className="p-4 border-t border-gray-800">
          <button
            onClick={() => navigate(`/copilot?resource=${encodeURIComponent(resource.resourceId)}`)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
          >
            <Bot className="w-4 h-4" />
            Ask Copilot
          </button>
        </div>
      </aside>
    </>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="flex items-center gap-2 text-gray-300 mb-2">
        {icon}
        <h3 className="text-sm font-medium">{title}</h3>
      </div>
      {children}
    </section>
  );
}
