import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { CircleDot, PlugZap, Save, Trash2, UserPlus, Users } from 'lucide-react';
import { apiFetch, errorMessage } from '../lib/api';
import { useTenant } from '../lib/tenant';
import { ErrorBanner, PageHeader, Panel, Spinner } from '../components/dashboard/primitives';

type WorkspaceUser = {
  id: string;
  tenant_id: string;
  name: string;
  email: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  status: 'active' | 'invited' | 'disabled';
};

const ROLES: WorkspaceUser['role'][] = ['owner', 'admin', 'member', 'viewer'];
const STATUSES: WorkspaceUser['status'][] = ['active', 'invited', 'disabled'];

export function SettingsPage() {
  const navigate = useNavigate();
  const { tenantId, tenantName, accountId, isConnected, clearTenant } = useTenant();
  const [users, setUsers] = useState<WorkspaceUser[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [savingUserId, setSavingUserId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [draft, setDraft] = useState({ name: '', email: '', role: 'member' as WorkspaceUser['role'] });

  const loadUsers = useCallback(async () => {
    if (!tenantId || tenantId === 'all') {
      setUsers([]);
      return;
    }
    setLoadingUsers(true);
    setError('');
    try {
      setUsers(await apiFetch<WorkspaceUser[]>(`/v1/tenants/${tenantId}/users`, { tenantId }));
    } catch (err) {
      setError(errorMessage(err));
      setUsers([]);
    } finally {
      setLoadingUsers(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const createUser = async () => {
    if (!tenantId || !draft.name.trim() || !draft.email.trim()) return;
    setSavingUserId('new');
    setError('');
    try {
      const created = await apiFetch<WorkspaceUser>(`/v1/tenants/${tenantId}/users`, {
        method: 'POST', tenantId,
        body: { name: draft.name.trim(), email: draft.email.trim(), role: draft.role, status: 'invited' },
      });
      setUsers((current) => [...current, created]);
      setDraft({ name: '', email: '', role: 'member' });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSavingUserId(null);
    }
  };

  const updateUser = async (user: WorkspaceUser) => {
    if (!tenantId) return;
    setSavingUserId(user.id);
    setError('');
    try {
      const updated = await apiFetch<WorkspaceUser>(`/v1/tenants/${tenantId}/users/${user.id}`, {
        method: 'PATCH', tenantId,
        body: { name: user.name, role: user.role, status: user.status },
      });
      setUsers((current) => current.map((item) => item.id === user.id ? updated : item));
    } catch (err) {
      setError(errorMessage(err));
      await loadUsers();
    } finally {
      setSavingUserId(null);
    }
  };

  const deleteUser = async (user: WorkspaceUser) => {
    if (!tenantId || !window.confirm(`Remove ${user.email} from this workspace?`)) return;
    setSavingUserId(user.id);
    setError('');
    try {
      await apiFetch(`/v1/tenants/${tenantId}/users/${user.id}`, { method: 'DELETE', tenantId });
      setUsers((current) => current.filter((item) => item.id !== user.id));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSavingUserId(null);
    }
  };

  return (
    <div>
      <PageHeader title="Settings" subtitle="Account connections and platform preferences." />

      <div className="space-y-6">
        {error && <ErrorBanner message={error} />}
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
        <Panel className="p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <div className="flex items-center gap-2 text-white font-medium">
                <Users className="w-4 h-4 text-emerald-400" />
                Workspace users
              </div>
              <p className="text-gray-500 text-sm mt-1">Members and roles for the selected workspace.</p>
            </div>
            <button
              type="button"
              onClick={() => void loadUsers()}
              disabled={loadingUsers || !tenantId || tenantId === 'all'}
              className="px-3 py-2 rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-600 disabled:opacity-40 text-sm"
            >
              Refresh
            </button>
          </div>

          {tenantId === 'all' ? (
            <p className="text-gray-500 text-sm">Choose a workspace to manage its users.</p>
          ) : loadingUsers ? (
            <div className="py-8"><Spinner /></div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_10rem_auto] gap-2 mb-5">
                <input value={draft.name} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} placeholder="Name" className="min-w-0 rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-emerald-500 focus:outline-none" />
                <input type="email" value={draft.email} onChange={(event) => setDraft((current) => ({ ...current, email: event.target.value }))} placeholder="Email address" className="min-w-0 rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-emerald-500 focus:outline-none" />
                <select value={draft.role} onChange={(event) => setDraft((current) => ({ ...current, role: event.target.value as WorkspaceUser['role'] }))} className="rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none">
                  {ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
                </select>
                <button type="button" onClick={() => void createUser()} disabled={savingUserId === 'new' || !draft.name.trim() || !draft.email.trim()} title="Add workspace user" className="flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-40"><UserPlus className="w-4 h-4" />Add</button>
              </div>

              {users.length === 0 ? (
                <p className="py-4 text-gray-500 text-sm">No workspace users yet.</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-gray-800">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="border-b border-gray-800 text-xs uppercase tracking-wide text-gray-500"><tr><th className="px-4 py-3 font-medium">User</th><th className="px-4 py-3 font-medium">Role</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 text-right font-medium">Actions</th></tr></thead>
                    <tbody className="divide-y divide-gray-800">
                      {users.map((user) => (
                        <tr key={user.id}>
                          <td className="px-4 py-3"><div className="text-white">{user.name}</div><div className="text-xs text-gray-500">{user.email}</div></td>
                          <td className="px-4 py-3"><select value={user.role} onChange={(event) => setUsers((current) => current.map((item) => item.id === user.id ? { ...item, role: event.target.value as WorkspaceUser['role'] } : item))} className="rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-sm text-white">{ROLES.map((role) => <option key={role} value={role}>{role}</option>)}</select></td>
                          <td className="px-4 py-3"><select value={user.status} onChange={(event) => setUsers((current) => current.map((item) => item.id === user.id ? { ...item, status: event.target.value as WorkspaceUser['status'] } : item))} className="rounded border border-gray-700 bg-gray-950 px-2 py-1.5 text-sm text-white">{STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}</select></td>
                          <td className="px-4 py-3"><div className="flex justify-end gap-2"><button type="button" onClick={() => void updateUser(user)} disabled={savingUserId === user.id} title="Save user" className="rounded p-2 text-gray-400 hover:bg-gray-800 hover:text-white disabled:opacity-40"><Save className="w-4 h-4" /></button><button type="button" onClick={() => void deleteUser(user)} disabled={savingUserId === user.id} title="Remove user" className="rounded p-2 text-red-300 hover:bg-red-500/10 disabled:opacity-40"><Trash2 className="w-4 h-4" /></button></div></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
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
