import { useCallback, useState } from 'react';

interface Insight {
  id: string;
  resource_id: string;
  resource_type: string;
  severity: string;
  category: string;
  issue: string;
  recommendation: string;
  confidence: string;
  estimated_monthly_waste: number;
  avg_cpu: number | null;
  instance_type: string | null;
  window_days: number | null;
}

interface ChatTurn {
  role: 'user' | 'assistant';
  text: string;
}

interface InsightsDashboardProps {
  apiBase: string;
  tenantId: string;
}

export function InsightsDashboard({ apiBase, tenantId }: InsightsDashboardProps) {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState<string>('');
  const [question, setQuestion] = useState('Why is this instance considered idle?');
  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [asking, setAsking] = useState(false);

  const headers = useCallback(
    () => ({ 'Content-Type': 'application/json', 'X-Tenant-ID': tenantId }),
    [tenantId]
  );

  const runAnalysis = useCallback(async () => {
    if (!tenantId) {
      setError('Connect an AWS account first.');
      return;
    }
    setAnalyzing(true);
    setError('');
    try {
      const res = await fetch(`${apiBase}/v1/insights/${tenantId}/analyze`, {
        method: 'POST',
        headers: headers(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Analysis failed');
      const found: Insight[] = data.insights || [];
      setInsights(found);
      if (found.length > 0) setSelectedId(found[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  }, [apiBase, tenantId, headers]);

  const askWhy = useCallback(async () => {
    if (!tenantId || !question.trim()) return;
    const q = question.trim();
    setChat((prev) => [...prev, { role: 'user', text: q }]);
    setAsking(true);
    try {
      const res = await fetch(`${apiBase}/v1/insights/${tenantId}/explain`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ question: q, insight_id: selectedId || undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Explanation failed');
      setChat((prev) => [...prev, { role: 'assistant', text: data.answer }]);
    } catch (e) {
      setChat((prev) => [
        ...prev,
        { role: 'assistant', text: e instanceof Error ? e.message : 'Explanation failed' },
      ]);
    } finally {
      setAsking(false);
    }
  }, [apiBase, tenantId, question, selectedId, headers]);

  const severityColor = (s: string) =>
    s === 'high' ? 'text-red-400' : s === 'medium' ? 'text-amber-400' : 'text-sky-400';

  return (
    <div className="mt-12 border-t border-gray-800 pt-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-white">Infrastructure Insights</h2>
          <p className="text-gray-400 text-sm">Idle / underutilized EC2 detection</p>
        </div>
        <button
          onClick={runAnalysis}
          disabled={analyzing || !tenantId}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-medium"
        >
          {analyzing ? 'Analyzing…' : 'Run analysis'}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {insights.length === 0 ? (
        <p className="text-gray-500 text-sm">
          No insights yet. Run analysis to scan this account for cost-optimization opportunities.
        </p>
      ) : (
        <div className="space-y-3">
          {insights.map((ins) => (
            <button
              key={ins.id}
              onClick={() => setSelectedId(ins.id)}
              className={`w-full text-left p-4 rounded-xl bg-[#111827] border ${
                selectedId === ins.id ? 'border-emerald-500' : 'border-gray-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-white font-medium">{ins.issue}</span>
                <span className={`text-xs uppercase ${severityColor(ins.severity)}`}>
                  {ins.severity} · {ins.confidence} confidence
                </span>
              </div>
              <p className="text-gray-300 text-sm mt-1">
                {ins.resource_id} ({ins.instance_type ?? 'unknown'}) — avg CPU{' '}
                {ins.avg_cpu}% over {ins.window_days}d
              </p>
              <p className="text-gray-400 text-sm mt-1">{ins.recommendation}</p>
              <p className="text-emerald-400 text-sm mt-1">
                ≈ ${ins.estimated_monthly_waste}/month potential savings
              </p>
            </button>
          ))}
        </div>
      )}

      {/* Chat */}
      <div className="mt-8">
        <h3 className="text-lg font-semibold text-white mb-3">Ask the Copilot</h3>
        <div className="space-y-3 mb-4">
          {chat.map((turn, i) => (
            <div
              key={i}
              className={`p-3 rounded-lg text-sm whitespace-pre-wrap ${
                turn.role === 'user'
                  ? 'bg-[#1f2937] text-gray-200'
                  : 'bg-[#0f1a2b] text-gray-100 border border-gray-800'
              }`}
            >
              {turn.text}
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && askWhy()}
            placeholder="Ask why an instance is idle…"
            className="flex-1 px-3 py-2 rounded-lg bg-[#0B0F17] border border-gray-700 text-white text-sm"
          />
          <button
            onClick={askWhy}
            disabled={asking || !tenantId}
            className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white text-sm font-medium"
          >
            {asking ? '…' : 'Ask'}
          </button>
        </div>
      </div>
    </div>
  );
}
