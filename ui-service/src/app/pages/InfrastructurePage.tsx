import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Server, RefreshCw, PlugZap } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { fetchEc2, fetchLambda, fetchRds } from '../lib/aws';
import { formatDateTime } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { Ec2Row, Insight, LambdaRow, RdsRow } from '../lib/types';
import {
  EmptyState,
  ErrorBanner,
  Panel,
  SeverityBadge,
  Spinner,
} from '../components/dashboard/primitives';
import { ResourceDrawer } from '../components/dashboard/ResourceDrawer';
import type { DrawerResource } from '../components/dashboard/ResourceDrawer';

type Tab = 'EC2' | 'RDS' | 'Lambda';
const PAGE_SIZE = 10;

export function InfrastructurePage() {
  const navigate = useNavigate();
  const { tenantId, region, isConnected } = useTenant();
  const [tab, setTab] = useState<Tab>('EC2');
  const [ec2, setEc2] = useState<Ec2Row[]>([]);
  const [rds, setRds] = useState<RdsRow[]>([]);
  const [lambda, setLambda] = useState<LambdaRow[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [page, setPage] = useState(0);
  const [drawer, setDrawer] = useState<DrawerResource | null>(null);

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    const warn: string[] = [];
    const [ec2R, rdsR, lambdaR, insR] = await Promise.allSettled([
      fetchEc2(tenantId, region),
      fetchRds(tenantId, region),
      fetchLambda(tenantId, region),
      apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId }),
    ]);
    if (ec2R.status === 'fulfilled') setEc2(ec2R.value);
    else warn.push('EC2');
    if (rdsR.status === 'fulfilled') setRds(rdsR.value);
    else warn.push('RDS');
    if (lambdaR.status === 'fulfilled') setLambda(lambdaR.value);
    else warn.push('Lambda');
    if (insR.status === 'fulfilled') setInsights(insR.value);
    setWarnings(warn);
    setLoading(false);
  }, [tenantId, region]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => setPage(0), [tab]);

  const flagged = useMemo(() => new Set(insights.map((i) => i.resource_id)), [insights]);
  const counts = { EC2: ec2.length, RDS: rds.length, Lambda: lambda.length };

  if (!isConnected) {
    return (
      <EmptyState
        icon={<PlugZap className="w-10 h-10" />}
        title="No AWS account connected"
        description="Connect an AWS account to discover infrastructure."
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
          <h1 className="text-2xl font-semibold text-white">Infrastructure Inventory</h1>
          <p className="text-gray-400 text-sm mt-1">Resources discovered through AWS Connector.</p>
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

      {warnings.length > 0 && (
        <ErrorBanner message={`Could not load: ${warnings.join(', ')}. The connector may be unavailable.`} />
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-gray-800">
        {(['EC2', 'RDS', 'Lambda'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px ${
              tab === t
                ? 'border-emerald-500 text-white'
                : 'border-transparent text-gray-400 hover:text-white'
            }`}
          >
            {t} <span className="text-gray-500">({counts[t]})</span>
          </button>
        ))}
      </div>

      {loading && counts[tab] === 0 ? (
        <Spinner label="Discovering resources…" />
      ) : tab === 'EC2' ? (
        <Ec2Table rows={ec2} page={page} setPage={setPage} flagged={flagged} onOpen={setDrawer} />
      ) : tab === 'RDS' ? (
        <RdsTable rows={rds} page={page} setPage={setPage} flagged={flagged} onOpen={setDrawer} />
      ) : (
        <LambdaTable rows={lambda} page={page} setPage={setPage} flagged={flagged} onOpen={setDrawer} />
      )}

      <ResourceDrawer resource={drawer} insights={insights} onClose={() => setDrawer(null)} />
    </div>
  );
}

/* ---------- tables ---------- */

function Paged<T>({
  rows,
  page,
  setPage,
  children,
}: {
  rows: T[];
  page: number;
  setPage: (n: number) => void;
  children: (pageRows: T[]) => React.ReactNode;
}) {
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  const slice = rows.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE);
  return (
    <Panel className="overflow-hidden">
      <div className="overflow-x-auto">{children(slice)}</div>
      <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800 text-xs text-gray-500">
        <span>
          {rows.length === 0 ? 'No resources' : `Page ${current + 1} of ${pages} · ${rows.length} total`}
        </span>
        <div className="flex gap-2">
          <button
            disabled={current === 0}
            onClick={() => setPage(current - 1)}
            className="px-2 py-1 rounded border border-gray-700 disabled:opacity-30 hover:border-gray-600"
          >
            Prev
          </button>
          <button
            disabled={current >= pages - 1}
            onClick={() => setPage(current + 1)}
            className="px-2 py-1 rounded border border-gray-700 disabled:opacity-30 hover:border-gray-600"
          >
            Next
          </button>
        </div>
      </div>
    </Panel>
  );
}

function HeadRow({ cols }: { cols: string[] }) {
  return (
    <thead>
      <tr className="text-left text-gray-400 border-b border-gray-800">
        {cols.map((c) => (
          <th key={c} className="px-4 py-3 font-medium whitespace-nowrap">
            {c}
          </th>
        ))}
      </tr>
    </thead>
  );
}

function StatusPill({ status }: { status: string }) {
  const s = status.toLowerCase();
  const color = ['running', 'available', 'active'].includes(s)
    ? 'text-emerald-400'
    : ['stopped', 'stopping', 'terminated'].includes(s)
    ? 'text-gray-400'
    : 'text-amber-400';
  return <span className={color}>{status}</span>;
}

function Ec2Table({
  rows,
  page,
  setPage,
  flagged,
  onOpen,
}: {
  rows: Ec2Row[];
  page: number;
  setPage: (n: number) => void;
  flagged: Set<string>;
  onOpen: (r: DrawerResource) => void;
}) {
  if (rows.length === 0) return <EmptyState icon={<Server className="w-10 h-10" />} title="No EC2 instances found" />;
  return (
    <Paged rows={rows} page={page} setPage={setPage}>
      {(slice) => (
        <table className="w-full text-sm">
          <HeadRow cols={['Instance ID', 'Name', 'State', 'Type', 'Region', '']} />
          <tbody>
            {slice.map((r) => (
              <tr
                key={r.resourceId}
                onClick={() =>
                  onOpen({
                    kind: 'EC2',
                    resourceId: r.resourceId,
                    title: r.name !== '—' ? r.name : r.resourceId,
                    meta: {
                      'Instance ID': r.resourceId,
                      Name: r.name,
                      Type: r.type,
                      State: r.status,
                      Region: r.region,
                      'Launch Time': formatDateTime(r.lastSeen),
                    },
                  })
                }
                className="border-b border-gray-800/60 hover:bg-white/[0.03] cursor-pointer"
              >
                <td className="px-4 py-3 font-mono text-xs text-white">{r.resourceId}</td>
                <td className="px-4 py-3 text-gray-300">{r.name}</td>
                <td className="px-4 py-3"><StatusPill status={r.status} /></td>
                <td className="px-4 py-3 text-gray-300">{r.type}</td>
                <td className="px-4 py-3 text-gray-400">{r.region}</td>
                <td className="px-4 py-3">{flagged.has(r.resourceId) && <SeverityBadge value="insight" />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Paged>
  );
}

function RdsTable({
  rows,
  page,
  setPage,
  flagged,
  onOpen,
}: {
  rows: RdsRow[];
  page: number;
  setPage: (n: number) => void;
  flagged: Set<string>;
  onOpen: (r: DrawerResource) => void;
}) {
  if (rows.length === 0) return <EmptyState icon={<Server className="w-10 h-10" />} title="No RDS databases found" />;
  return (
    <Paged rows={rows} page={page} setPage={setPage}>
      {(slice) => (
        <table className="w-full text-sm">
          <HeadRow cols={['Identifier', 'Engine', 'Status', 'Class', 'Region', '']} />
          <tbody>
            {slice.map((r) => (
              <tr
                key={r.resourceId}
                onClick={() =>
                  onOpen({
                    kind: 'RDS',
                    resourceId: r.resourceId,
                    title: r.name,
                    meta: {
                      Identifier: r.resourceId,
                      Engine: r.engine,
                      Status: r.status,
                      Class: r.instanceClass,
                      Region: r.region,
                      Created: formatDateTime(r.lastSeen),
                    },
                  })
                }
                className="border-b border-gray-800/60 hover:bg-white/[0.03] cursor-pointer"
              >
                <td className="px-4 py-3 font-mono text-xs text-white">{r.resourceId}</td>
                <td className="px-4 py-3 text-gray-300">{r.engine}</td>
                <td className="px-4 py-3"><StatusPill status={r.status} /></td>
                <td className="px-4 py-3 text-gray-300">{r.instanceClass}</td>
                <td className="px-4 py-3 text-gray-400">{r.region}</td>
                <td className="px-4 py-3">{flagged.has(r.resourceId) && <SeverityBadge value="insight" />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Paged>
  );
}

function LambdaTable({
  rows,
  page,
  setPage,
  flagged,
  onOpen,
}: {
  rows: LambdaRow[];
  page: number;
  setPage: (n: number) => void;
  flagged: Set<string>;
  onOpen: (r: DrawerResource) => void;
}) {
  if (rows.length === 0) return <EmptyState icon={<Server className="w-10 h-10" />} title="No Lambda functions found" />;
  return (
    <Paged rows={rows} page={page} setPage={setPage}>
      {(slice) => (
        <table className="w-full text-sm">
          <HeadRow cols={['Function Name', 'Runtime', 'Memory', 'Last Modified', '']} />
          <tbody>
            {slice.map((r) => (
              <tr
                key={r.resourceId}
                onClick={() =>
                  onOpen({
                    kind: 'Lambda',
                    resourceId: r.resourceId,
                    title: r.name,
                    meta: {
                      'Function Name': r.name,
                      Runtime: r.runtime,
                      Memory: `${r.memoryMb} MB`,
                      'Last Modified': formatDateTime(r.lastSeen),
                    },
                  })
                }
                className="border-b border-gray-800/60 hover:bg-white/[0.03] cursor-pointer"
              >
                <td className="px-4 py-3 text-white">{r.name}</td>
                <td className="px-4 py-3 text-gray-300">{r.runtime}</td>
                <td className="px-4 py-3 text-gray-400">{r.memoryMb} MB</td>
                <td className="px-4 py-3 text-gray-400">{formatDateTime(r.lastSeen)}</td>
                <td className="px-4 py-3">{flagged.has(r.resourceId) && <SeverityBadge value="insight" />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Paged>
  );
}
