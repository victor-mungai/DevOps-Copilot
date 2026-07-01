import { useNavigate } from 'react-router';
import { CircleDot, PlugZap } from 'lucide-react';
import { useTenant } from '../lib/tenant';
import { PageHeader, Panel } from '../components/dashboard/primitives';

export function SettingsPage() {
  const navigate = useNavigate();
  const { tenantId, tenantName, accountId, isConnected, clearTenant } = useTenant();

  return (
    <div>
      <PageHeader title="Settings" subtitle="Account connections and platform preferences." />

      <div className="space-y-6">
        {/* AWS Accounts — real data from tenant context */}
        <Panel className="p-5">
          <h2 className="text-white font-medium mb-4">AWS Accounts</h2>
          {isConnected ? (
            <div className="rounded-lg border border-gray-800 divide-y divide-gray-800">
              <Row label="Tenant" value={tenantName || '—'} />
              <Row label="Tenant ID" value={tenantId} mono />
              <Row label="AWS Account ID" value={accountId || 'Not verified'} mono />
              <Row
                label="Connection Status"
                value={
                  <span className="inline-flex items-center gap-1.5 text-emerald-400">
                    <CircleDot className="w-3.5 h-3.5" />
                    {accountId ? 'Connected' : 'Pending verification'}
                  </span>
                }
              />
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <p className="text-gray-400 text-sm">No AWS account connected yet.</p>
              <button
                onClick={() => navigate('/onboarding')}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
              >
                <PlugZap className="w-4 h-4" />
                Connect AWS
              </button>
            </div>
          )}
          {isConnected && (
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => navigate('/onboarding')}
                className="px-3 py-2 rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-600 text-sm"
              >
                Connect another account
              </button>
              <button
                onClick={clearTenant}
                className="px-3 py-2 rounded-lg border border-red-500/30 text-red-300 hover:bg-red-500/10 text-sm"
              >
                Disconnect
              </button>
            </div>
          )}
        </Panel>

        {/* User settings — future */}
        <Panel className="p-5 opacity-70">
          <h2 className="text-white font-medium mb-2">User Settings</h2>
          <p className="text-gray-500 text-sm">
            Notifications, profile and API keys are planned for a future phase.
          </p>
        </Panel>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3 text-sm">
      <span className="text-gray-400">{label}</span>
      <span className={`text-white ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  );
}
