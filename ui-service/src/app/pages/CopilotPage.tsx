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
const QUICK_ACTIONS = [
  'Find idle resources',
  'Show cost optimization opportunities',
  'Show unhealthy infrastructure',
  'Summarize my environment',
];

const DAY_ORDER: DayGroup[] = ['Today', 'Yesterday', 'Older'];

export function CopilotPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { tenantId, region, isConnected } = useTenant();
  const focusedResource = searchParams.get('resource') || '';
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  const [input, setInput] = useState('');
  const [asking, setAsking] = useState(false);
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

  const startNew = useCallback(() => {
    setActiveId('');
    setInput('');
  }, []);

  const ask = useCallback(
    async (questionText: string) => {
      const q = questionText.trim();
      if (!q || !tenantId || asking) return;
      setInput('');
      setAsking(true);

      // Sliding-window history: prior turns of the active conversation, capped.
      const priorTurns = conversations.find((c) => c.id === activeId)?.turns ?? [];
      const history = priorTurns.slice(-10).map((t) => ({ role: t.role, content: t.text }));

      // Ensure there's an active conversation; create one on first message.
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
          },
        });
        persistAssistant(convId, data.answer);
      } catch (e) {
        persistAssistant(convId, `⚠️ ${errorMessage(e)}`);
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
    [tenantId, region, focusedResource, activeId, conversations, asking, persist]
  );

  // Resource-aware entry: when the drawer deep-links here with ?resource=,
  // start a focused conversation and auto-ask for a structured analysis. Fires
  // once per resource param.
  const autoAsked = useRef<string>('');
  useEffect(() => {
    if (!focusedResource || asking) return;
    if (autoAsked.current === focusedResource) return;
    autoAsked.current = focusedResource;
    setActiveId('');
    void ask(
      `Analyze resource ${focusedResource}: give me its current state, root cause, ` +
        `metric evidence, and a recommendation.`
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusedResource]);

  if (!isConnected) {
    return (
      <EmptyState
        icon={<PlugZap className="w-10 h-10" />}
        title="No AWS account connected"
        description="Connect an AWS account so the Copilot can reason about your infrastructure."
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

  const grouped = groupByDay(conversations);

  return (
    <div className="h-[calc(100vh-7rem)] flex gap-6">
      {/* Left: conversation history */}
      <aside className="w-72 shrink-0 flex flex-col">
        <button
          onClick={startNew}
          className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium mb-3"
        >
          <Plus className="w-4 h-4" />
          New chat
        </button>
        <Panel className="flex-1 overflow-y-auto p-2">
          {conversations.length === 0 ? (
            <p className="text-gray-500 text-sm p-3">No conversations yet.</p>
          ) : (
            DAY_ORDER.filter((d) => grouped[d].length > 0).map((day) => (
              <div key={day} className="mb-2">
                <p className="px-2 py-1 text-xs uppercase tracking-wide text-gray-500">{day}</p>
                {grouped[day].map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setActiveId(c.id)}
                    className={`w-full flex items-center gap-2 text-left p-2 rounded-lg text-sm transition-colors ${
                      activeId === c.id
                        ? 'bg-emerald-600/15 border border-emerald-600/30 text-white'
                        : 'text-gray-300 hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5 shrink-0 text-gray-500" />
                    <span className="truncate">{c.title}</span>
                  </button>
                ))}
              </div>
            ))
          )}
        </Panel>
      </aside>

      {/* Right: chat */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-lg font-semibold text-white">AI Copilot</h1>
          {focusedResource && (
            <span className="flex items-center gap-1 ml-2 px-2 py-0.5 rounded-full bg-violet-500/15 border border-violet-500/30 text-violet-300 text-xs">
              focused: {focusedResource}
              <button
                onClick={() => setSearchParams({})}
                className="ml-1 text-violet-400 hover:text-white"
                aria-label="Clear focus"
              >
                ×
              </button>
            </span>
          )}
        </div>

        <Panel className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {!active || active.turns.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <Sparkles className="w-8 h-8 text-emerald-400 mb-3" />
                <p className="text-white font-medium">Ask anything about your environment</p>
                <p className="text-gray-500 text-sm mt-1 max-w-sm">
                  Answers come back as Summary · Root Cause · Impact · Recommendation.
                </p>
              </div>
            ) : (
              active.turns.map((turn, i) => <Bubble key={i} turn={turn} />)
            )}
            {asking && (
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <Bot className="w-4 h-4" />
                <span className="animate-pulse">Thinking…</span>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Quick actions */}
          <div className="px-5 pt-3 flex flex-wrap gap-2 border-t border-gray-800">
            {QUICK_ACTIONS.map((s) => (
              <button
                key={s}
                onClick={() => void ask(s)}
                disabled={asking}
                className="px-3 py-1.5 rounded-full border border-gray-700 text-gray-300 hover:text-white hover:border-gray-600 text-xs disabled:opacity-40"
              >
                {s}
              </button>
            ))}
          </div>

          {/* Composer */}
          <div className="p-4 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void ask(input)}
              placeholder="Ask the Copilot…"
              className="flex-1 px-3 py-2.5 rounded-lg bg-[#0B0F17] border border-gray-700 text-white text-sm focus:outline-none focus:border-emerald-500"
            />
            <button
              onClick={() => void ask(input)}
              disabled={asking || !input.trim()}
              className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-medium flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Bubble({ turn }: { turn: { role: 'user' | 'assistant'; text: string } }) {
  const isUser = turn.role === 'user';
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
          isUser ? 'bg-sky-600' : 'bg-emerald-600'
        }`}
      >
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
      </div>
      <div
        className={`max-w-[75%] p-3 rounded-xl text-sm whitespace-pre-wrap leading-relaxed ${
          isUser
            ? 'bg-sky-600/15 text-gray-100 border border-sky-600/20'
            : 'bg-[#0f1a2b] text-gray-100 border border-gray-800'
        }`}
      >
        {turn.text}
      </div>
    </div>
  );
}
