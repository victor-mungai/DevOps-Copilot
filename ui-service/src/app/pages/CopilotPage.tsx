import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { Bot, Send, PlugZap, Sparkles, User, Plus, MessageSquare } from 'lucide-react';
import { apiFetch, errorMessage } from '../lib/api';
import { useTenant } from '../lib/tenant';
import type { ExplainResponse } from '../lib/types';
import {
  loadConversations,
  saveConversations,
  newConversation,
  groupByDay,
} from '../lib/conversations';
import type { Conversation, DayGroup } from '../lib/conversations';
import { EmptyState, Panel } from '../components/dashboard/primitives';

// Quick actions execute on click (no typing required).
const SUGGESTED = [
  'Why is EC2 costing more?',
  'Which resources are underutilized?',
  'What should we optimize first?',
  'Why did our environment health drop?',
];

export function CopilotPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { tenantId, region, isConnected } = useTenant();
  const focusedResource = searchParams.get('resource') || searchParams.get('prompt') || '';
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  const [input, setInput] = useState('');
  const [asking, setAsking] = useState(false);
  const [model, setModel] = useState<'auto' | 'chatgpt' | 'claude'>('auto');
  const [apiKey, setApiKey] = useState('');
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!tenantId) return;
    const list = loadConversations(tenantId);
    setConversations(list);
    setActiveId(list[0]?.id ?? '');
  }, [tenantId]);

  const active = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? null,
    [conversations, activeId]
  );

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [active?.turns, asking]);

  const persist = useCallback(
    (list: Conversation[]) => {
      setConversations(list);
      if (tenantId) saveConversations(tenantId, list);
    },
    [tenantId]
  );

  const ask = useCallback(
    async (questionText: string) => {
      const q = questionText.trim();
      if (!q || !tenantId || asking) return;
      setInput('');
      setAsking(true);

      const priorTurns = conversations.find((c) => c.id === activeId)?.turns ?? [];
      const history = priorTurns.slice(-10).map((t) => ({ role: t.role, content: t.text }));

      let convId = activeId;
      let working: Conversation[];
      if (!convId) {
        const conv = newConversation(q);
        convId = conv.id;
        conv.turns.push({ role: 'user', text: q });
        working = [conv, ...conversations];
        setActiveId(convId);
      } else {
        working = conversations.map((c) =>
          c.id === convId
            ? { ...c, turns: [...c.turns, { role: 'user', text: q }], updatedAt: Date.now() }
            : c
        );
      }
      persist(working);

      try {
        const data = await apiFetch<ExplainResponse>(`/v1/insights/${tenantId}/explain`, {
          method: 'POST',
          tenantId,
          body: {
            question: q,
            region,
            resource_id: focusedResource || undefined,
            history,
            model,
            ...(apiKey ? { api_key: apiKey } : {}),
          },
        });
        persistAssistant(convId, data.answer);
      } catch (e) {
        persistAssistant(convId, `Unable to query Copilot analysis: ${errorMessage(e)}`);
      } finally {
        setAsking(false);
      }

      function persistAssistant(id: string, text: string) {
        setConversations((prev) => {
          const next = prev.map((c) =>
            c.id === id
              ? { ...c, turns: [...c.turns, { role: 'assistant' as const, text }], updatedAt: Date.now() }
              : c
          );
          if (tenantId) saveConversations(tenantId, next);
          return next;
        });
      }
    },
    [tenantId, region, focusedResource, activeId, conversations, asking, persist, model, apiKey]
  );

  if (!isConnected) {
    return (
      <div className="py-16 text-center text-gray-400 font-sans">
        Connect an AWS account to ask Copilot about your environment.
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 font-sans">
      <div>
        <h1 className="text-xl font-semibold text-white">Copilot</h1>
        <p className="text-sm text-gray-400 mt-0.5">Ask about your AWS environment.</p>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <label className="text-xs text-gray-400">Model
          <select value={model} onChange={(e) => setModel(e.target.value as typeof model)} className="ml-2 bg-[#0B0F17] border border-gray-700 rounded px-2 py-1.5 text-white">
            <option value="auto">Configured</option>
            <option value="chatgpt">ChatGPT</option>
            <option value="claude">Claude</option>
          </select>
        </label>
        <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="Optional API key" autoComplete="off" className="bg-[#0B0F17] border border-gray-700 rounded px-2 py-1.5 text-xs text-white" />
      </div>

      {/* Composer */}
      <div className="rounded-xl bg-[#111827] border border-gray-800 p-4 shadow-lg space-y-3">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void ask(input)}
            placeholder="Why did our AWS spend increase this month?"
            className="flex-1 px-3.5 py-2.5 rounded-lg bg-[#0B0F17] border border-gray-700 text-white text-sm focus:outline-none focus:border-emerald-500"
          />
          <button
            onClick={() => void ask(input)}
            disabled={asking || !input.trim()}
            className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-medium flex items-center gap-2 shrink-0"
          >
            <Send className="w-4 h-4" />
            Ask
          </button>
        </div>

        {/* Suggested Pills */}
        <div className="pt-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Suggested:</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED.map((s) => (
              <button
                key={s}
                onClick={() => void ask(s)}
                disabled={asking}
                className="px-3 py-1.5 rounded-lg bg-[#0B0F17] border border-gray-800 text-gray-300 hover:text-white hover:border-gray-700 text-xs font-medium transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      {active && active.turns.length > 0 && (
        <div className="space-y-4 pt-2">
          {active.turns.map((turn, i) => (
            <div
              key={i}
              className={`p-5 rounded-xl border text-sm leading-relaxed ${
                turn.role === 'user'
                  ? 'bg-emerald-600/10 border-emerald-600/20 text-white font-medium'
                  : 'bg-[#111827] border-gray-800 text-gray-200 whitespace-pre-wrap'
              }`}
            >
              {turn.role === 'assistant' && (
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3">
                  <Bot className="w-4 h-4" /> Copilot Operational Analysis
                </div>
              )}
              {turn.text}
            </div>
          ))}
          {asking && (
            <div className="p-4 rounded-xl bg-[#111827] border border-gray-800 text-gray-400 text-xs flex items-center gap-2">
              <Bot className="w-4 h-4 text-emerald-400 animate-pulse" />
              <span className="animate-pulse">Analyzing AWS telemetry…</span>
            </div>
          )}
          <div ref={endRef} />
        </div>
      )}
    </div>
  );
}
