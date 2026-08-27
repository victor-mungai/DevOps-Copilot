import { useState } from 'react';
import { Calendar, ChevronDown, Check } from 'lucide-react';
import { TIME_PERIOD_OPTIONS, useTenant } from '../lib/tenant';
import type { TimePeriodKey } from '../lib/tenant';

export function TimePeriodSelector() {
  const { timePeriod, setTimePeriod, customRange, setCustomRange } = useTenant();
  const [open, setOpen] = useState(false);
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [tempStart, setTempStart] = useState(customRange.start);
  const [tempEnd, setTempEnd] = useState(customRange.end);

  const activeOption = TIME_PERIOD_OPTIONS.find((o) => o.key === timePeriod) ?? TIME_PERIOD_OPTIONS[0];

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-800 bg-[#111827] text-xs font-semibold text-gray-200 hover:border-gray-700 transition-colors"
        >
          <Calendar className="w-3.5 h-3.5 text-emerald-400" />
          <span>{activeOption.label}</span>
          <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
        </button>

        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <div className="absolute right-0 mt-2 w-48 rounded-xl bg-[#111827] border border-gray-800 shadow-xl z-20 py-1 font-sans">
              <p className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-gray-500">Time Period</p>
              {TIME_PERIOD_OPTIONS.map((o) => (
                <button
                  key={o.key}
                  onClick={() => {
                    if (o.key === 'custom') {
                      setShowCustomModal(true);
                      setOpen(false);
                    } else {
                      setTimePeriod(o.key);
                      setOpen(false);
                    }
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left ${
                    timePeriod === o.key ? 'bg-emerald-600/15 text-emerald-400 font-semibold' : 'text-gray-300 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <span>{o.label}</span>
                  {timePeriod === o.key && <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Custom Date Range Modal */}
      {showCustomModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 w-full max-w-sm space-y-4">
            <h3 className="text-sm font-semibold text-white">Custom Date Range</h3>
            
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-gray-400 block mb-1">Start Date</label>
                <input
                  type="date"
                  value={tempStart}
                  onChange={(e) => setTempStart(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#0B0F17] border border-gray-700 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="text-gray-400 block mb-1">End Date</label>
                <input
                  type="date"
                  value={tempEnd}
                  onChange={(e) => setTempEnd(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#0B0F17] border border-gray-700 text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowCustomModal(false)}
                className="px-3 py-1.5 rounded-lg border border-gray-700 text-gray-300 text-xs hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setCustomRange({ start: tempStart, end: tempEnd });
                  setTimePeriod('custom');
                  setShowCustomModal(false);
                }}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
              >
                Apply Range
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
