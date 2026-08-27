import { useState } from 'react';
import { useNavigate } from 'react-router';
import { Check, ChevronDown, Layers, Plus, Globe } from 'lucide-react';
import { useTenant } from '../lib/tenant';

export function WorkspaceSelector() {
  const navigate = useNavigate();
  const { workspaces, activeId, tenantName, switchWorkspace, isAllAccounts } = useTenant();
  const [open, setOpen] = useState(false);

  if (workspaces.length === 0) return null;

  const currentLabel = isAllAccounts ? `All Accounts (${workspaces.length})` : tenantName || 'Account';

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-800 bg-[#111827] text-xs font-semibold text-gray-200 hover:border-gray-700 transition-colors"
      >
        {isAllAccounts ? (
          <Globe className="w-3.5 h-3.5 text-emerald-400" />
        ) : (
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
        )}
        <span className="max-w-[180px] truncate">{currentLabel}</span>
        <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 mt-2 w-64 rounded-xl bg-[#111827] border border-gray-800 shadow-xl z-20 py-1 font-sans">
            <p className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-500">Scope Selector</p>
            
            {/* All Accounts Option */}
            <button
              onClick={() => {
                switchWorkspace('all');
                setOpen(false);
              }}
              className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-xs font-semibold ${
                isAllAccounts ? 'bg-emerald-600/15 text-emerald-400' : 'text-gray-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Globe className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="truncate">All Accounts ({workspaces.length})</span>
              </div>
              {isAllAccounts && <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
            </button>

            <div className="h-px bg-gray-800 my-1" />

            <p className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-gray-500">Connected Accounts</p>

            {workspaces.map((w) => {
              const isSelected = !isAllAccounts && w.tenantId === activeId;
              return (
                <button
                  key={w.tenantId}
                  onClick={() => {
                    switchWorkspace(w.tenantId);
                    setOpen(false);
                  }}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-xs text-left ${
                    isSelected ? 'bg-emerald-600/15 text-emerald-400 font-semibold' : 'text-gray-300 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{w.tenantName || 'AWS Account'}</span>
                    <span className="block text-[11px] text-gray-500 font-mono truncate">
                      {w.accountId || w.tenantId}
                    </span>
                  </span>
                  {isSelected && <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                </button>
              );
            })}

            <div className="border-t border-gray-800 mt-1 pt-1">
              <button
                onClick={() => {
                  setOpen(false);
                  navigate('/onboarding?new=1');
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-emerald-400 hover:bg-white/5"
              >
                <Plus className="w-3.5 h-3.5" />
                Onboard another AWS account
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
