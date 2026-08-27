import { useState } from 'react';
import { Check, ChevronDown, Globe } from 'lucide-react';
import { AWS_REGIONS, useTenant } from '../lib/tenant';

// Global AWS region selector. The active region is part of the workspace context
// (persisted) and is sent with every AWS resource call, so switching it re-scopes
// EC2/RDS/Lambda across the whole app.
export function RegionSelector() {
  const { region, setRegion, isConnected } = useTenant();
  const [open, setOpen] = useState(false);

  if (!isConnected) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-gray-700 text-sm text-gray-200 hover:border-gray-600"
      >
        <Globe className="w-4 h-4 text-sky-400" />
        <span>{region}</span>
        <ChevronDown className="w-4 h-4 text-gray-500" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 mt-2 w-52 max-h-80 overflow-y-auto rounded-lg bg-[#111827] border border-gray-800 shadow-xl z-20 py-1">
            <p className="px-3 py-1.5 text-xs uppercase tracking-wide text-gray-500">Region</p>
            {AWS_REGIONS.map((r) => (
              <button
                key={r}
                onClick={() => {
                  setRegion(r);
                  setOpen(false);
                }}
                className="w-full flex items-center justify-between gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-white/5 hover:text-white"
              >
                <span className="font-mono text-xs">{r}</span>
                {r === region && <Check className="w-4 h-4 text-emerald-400 shrink-0" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
