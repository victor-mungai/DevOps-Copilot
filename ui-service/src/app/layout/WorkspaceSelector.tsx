import { useState } from 'react';
import { useNavigate } from 'react-router';
import { Check, ChevronDown, Layers, Plus } from 'lucide-react';
import { useTenant } from '../lib/tenant';

// Workspace dropdown in the top nav. Switches the active AWS workspace and
// offers a shortcut to connect another account. Becomes important as customers
// add multiple AWS accounts.
export function WorkspaceSelector() {
  const navigate = useNavigate();
  const { workspaces, activeId, tenantName, tenantId, switchWorkspace } = useTenant();
  const [open, setOpen] = useState(false);

  if (workspaces.length === 0) return null;

  const label = (w: { tenantName: string; tenantId: string }) =>
    w.tenantName || `${w.tenantId.slice(0, 8)}…`;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-gray-700 text-sm text-gray-200 hover:border-gray-600"
      >
        <Layers className="w-4 h-4 text-emerald-400" />
        <span className="max-w-[160px] truncate">{tenantName || `${tenantId.slice(0, 8)}…`}</span>
        <ChevronDown className="w-4 h-4 text-gray-500" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 mt-2 w-64 rounded-lg bg-[#111827] border border-gray-800 shadow-xl z-20 py-1">
            <p className="px-3 py-1.5 text-xs uppercase tracking-wide text-gray-500">Workspaces</p>
            {workspaces.map((w) => (
              <button
                key={w.tenantId}
                onClick={() => {
                  switchWorkspace(w.tenantId);
                  setOpen(false);
                }}
                className="w-full flex items-center justify-between gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-white/5 hover:text-white"
              >
                <span className="min-w-0">
                  <span className="block truncate">{label(w)}</span>
                  <span className="block text-xs text-gray-500 truncate">
                    {w.accountId ? `AWS ${w.accountId}` : 'Not connected'}
                  </span>
                </span>
                {w.tenantId === activeId && <Check className="w-4 h-4 text-emerald-400 shrink-0" />}
              </button>
            ))}
            <div className="border-t border-gray-800 mt-1 pt-1">
              <button
                onClick={() => {
                  setOpen(false);
                  navigate('/onboarding?new=1');
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-emerald-400 hover:bg-white/5"
              >
                <Plus className="w-4 h-4" />
                Connect another account
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
