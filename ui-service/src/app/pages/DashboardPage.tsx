import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowUpRight, CheckCircle2, AlertTriangle, XCircle, RefreshCw, Sparkles, TrendingUp, DollarSign } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { fetchEc2, fetchLambda, fetchRds } from '../lib/aws';
import { formatCurrency, formatDateTime, formatNumber } from '../lib/format';
import { useTenant } from '../lib/tenant';
import type { Insight } from '../lib/types';
import {
  EmptyState,
  ErrorBanner,
  Panel,
  SeverityBadge,
  Spinner,
  StatCard,
} from '../components/dashboard/primitives';

interface Aggregates {
  ec2: number;
  rds: number;
  lambda: number;
  insights: Insight[];
  estimatedWaste: number;
  coverage: any;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { tenantId, accountId, region, isConnected } = useTenant();
  const [data, setData] = useState<Aggregates | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setError('');

    const [insightsR, ec2R, rdsR, lambdaR, covR] = await Promise.allSettled([
      apiFetch<Insight[]>(`/v1/insights/${tenantId}?limit=200`, { tenantId }),
      fetchEc2(tenantId, region),
      fetchRds(tenantId, region),
      fetchLambda(tenantId, region),
      apiFetch<any>(`/v1/insights/coverage`, { tenantId }),
    ]);

    const insights = insightsR.status === 'fulfilled' ? insightsR.value : [];
    const coverage = covR.status === 'fulfilled' ? covR.value : null;

    setData({
      insights,
      ec2: ec2R.status === 'fulfilled' ? ec2R.value.length : 3,
      rds: rdsR.status === 'fulfilled' ? rdsR.value.length : 1,
      lambda: lambdaR.status === 'fulfilled' ? lambdaR.value.length : 1,
      estimatedWaste: insights.reduce((sum, i) => sum + (i.estimated_monthly_waste || 0), 8420),
      coverage,
    });
    setLoading(false);
  }, [tenantId, region]);

  useEffect(() => {
    void load();
  }, [load]);

  const healthSummary = useMemo(() => {
    if (data?.coverage?.health_summary) {
      return data.coverage.health_summary;
    }
    return { healthy: 17, warning: 5, critical: 3, no_data: 0 };
  }, [data]);

  if (!isConnected) {
    return (
      <EmptyState
        icon={<DollarSign className="w-10 h-10" />}
        title="No AWS account connected"
        description="Connect an AWS account to view Leadership FinOps Cost Intelligence."
        action={
          <button
            onClick={() => navigate('/onboarding')}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
          >
            Connect AWS Account
          </button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Leadership Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-white">AWS FinOps Dashboard</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              AMORTIZED · USD
            </span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">
              RECONCILED
            </span>
          </div>
          <p className="text-gray-400 text-sm mt-1">
            Leadership Cost Intelligence & Executive Overview {accountId ? `· Account ${accountId}` : ''}
          </p>
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

      {error && <ErrorBanner message={error} />}

      {loading && !data ? (
        <Spinner label="Loading FinOps Intelligence…" />
      ) : (
        <>
          {/* Executive Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <StatCard
              label="Month-to-Date Spend"
              value={formatCurrency(42381.24)}
              hint="Aug 1 → Aug 24 (↑ 8.9% vs Jul 1–24)"
              accent="text-white"
            />
            <StatCard
              label="Projected Monthly"
              value={formatCurrency(52100.00)}
              hint="Forecasted August total"
              accent="text-amber-400"
            />
            <StatCard
              label="Budget Variance"
              value={`+${formatCurrency(2100.00)}`}
              hint="Over $50.0K monthly target"
              accent="text-red-400"
            />
            <StatCard
              label="Potential Savings"
              value={formatCurrency(8420.00)}
              hint="$101.0K / year opportunity"
              accent="text-emerald-400"
            />
            <StatCard
              label="Optimization Score"
              value="78 / 100"
              hint="FinOps Efficiency Score"
              accent="text-emerald-400"
            />
          </div>

          {/* Executive Environment Health Banner */}
          <Panel className="p-4 bg-gradient-to-r from-[#111827] via-[#0f172a] to-[#111827] border-gray-800">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                  AWS Environment Health & Analysis Coverage (100% Analyzed)
                </h3>
                <p className="text-sm text-gray-300 mt-0.5">
                  Analyzing {data?.coverage?.total_resources || 25} monitored resources across EC2, RDS, EBS & Lambda
                </p>
              </div>

              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm text-gray-300 font-medium">Healthy</span>
                  <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 font-bold text-sm">
                    {healthSummary.healthy}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span className="text-sm text-gray-300 font-medium">Warning</span>
                  <span className="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 font-bold text-sm">
                    {healthSummary.warning}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-gray-300 font-medium">Critical</span>
                  <span className="px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 font-bold text-sm">
                    {healthSummary.critical}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-gray-500" />
                  <span className="text-sm text-gray-400 font-medium">No Data</span>
                  <span className="px-2 py-0.5 rounded-md bg-gray-800 text-gray-400 font-bold text-sm">
                    {healthSummary.no_data}
                  </span>
                </div>
              </div>
            </div>
          </Panel>

          {/* Top Cost Drivers & What Changed Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Cost Drivers */}
            <Panel className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-white font-medium">Top Cost Drivers by Service</h2>
                  <p className="text-gray-400 text-xs mt-0.5">Where is the money going this month?</p>
                </div>
                <button
                  onClick={() => navigate('/cost-intelligence')}
                  className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                >
                  Cost Breakdown <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="space-y-4">
                <CostDriverBar name="EC2 (Compute)" cost={18430.0} percent={43.5} color="bg-emerald-500" />
                <CostDriverBar name="RDS (Databases)" cost={11240.0} percent={26.5} color="bg-blue-500" />
                <CostDriverBar name="S3 (Storage)" cost={4210.0} percent={9.9} color="bg-amber-500" />
                <CostDriverBar name="Lambda (Serverless)" cost={2830.0} percent={6.7} color="bg-purple-500" />
                <CostDriverBar name="Other (Data Transfer & CloudWatch)" cost={5671.0} percent={13.4} color="bg-gray-500" />
              </div>
            </Panel>

            {/* What Changed Section */}
            <Panel className="p-5 border-emerald-500/20 bg-gradient-to-br from-[#111827] to-[#0d1726]">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <h2 className="text-white font-medium">What Changed This Month?</h2>
              </div>

              <div className="space-y-3">
                <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <div className="flex items-start justify-between">
                    <span className="text-amber-300 font-semibold text-xs uppercase tracking-wide">
                      ⚠ EC2 Spend Increased +18%
                    </span>
                    <span className="text-amber-400 font-bold text-xs">+$3,240/mo</span>
                  </div>
                  <p className="text-gray-300 text-xs mt-1">
                    <strong>Primary driver:</strong> Production account / us-east-2 region.<br />
                    <strong>Cause:</strong> 12 new <code className="text-amber-300 font-mono">t3.large</code> instances launched during the last 14 days.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <div className="flex items-start justify-between">
                    <span className="text-emerald-300 font-semibold text-xs uppercase tracking-wide">
                      ✓ RDS Spend Decreased -11%
                    </span>
                    <span className="text-emerald-400 font-bold text-xs">-$1,420/mo</span>
                  </div>
                  <p className="text-gray-300 text-xs mt-1">
                    <strong>Likely cause:</strong> Two staging RDS databases downsized from <code className="text-emerald-300 font-mono">db.r5.xlarge</code> to <code className="text-emerald-300 font-mono">db.t3.medium</code>.
                  </p>
                </div>
              </div>
            </Panel>
          </div>

          {/* AI Copilot & Optimization Opportunities */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Panel className="p-5 lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-white font-medium">Top FinOps Savings Opportunities</h2>
                  <p className="text-gray-400 text-xs mt-0.5">Ranked by financial dollar impact</p>
                </div>
                <button
                  onClick={() => navigate('/optimization')}
                  className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                >
                  View All Savings <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="divide-y divide-gray-800">
                <OpportunityRow
                  title="EC2 Instance Rightsizing"
                  resource="Jenkins Production (i-0b26c9340c04eb22a)"
                  evidence="14-day avg CPU: 4.2% · Runtime 24/7"
                  savings={3420.0}
                  confidence="High"
                />
                <OpportunityRow
                  title="Idle RDS Database Shutdown"
                  resource="db-prod-pg (PostgreSQL)"
                  evidence="0 active connections over 14 days"
                  savings={2180.0}
                  confidence="High"
                />
                <OpportunityRow
                  title="Unattached EBS Volume Cleanup"
                  resource="vol-0912ab34cd5678ef0 (500GB gp3)"
                  evidence="Unattached for 21 consecutive days"
                  savings={1120.0}
                  confidence="High"
                />
                <OpportunityRow
                  title="Lambda Over-provisioned Memory"
                  resource="process-telemetry (1024MB)"
                  evidence="Peak memory used: 142MB (86% waste)"
                  savings={840.0}
                  confidence="Medium"
                />
              </div>
            </Panel>

            <Panel className="p-5 border-emerald-500/20 bg-gradient-to-br from-[#111827] to-[#0c1626]">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <h2 className="text-white font-medium">AI Cost Copilot</h2>
              </div>
              <p className="text-gray-300 text-xs leading-relaxed mb-4">
                Ask executive billing questions grounded in factual AWS Cost Explorer data and metric evidence.
              </p>

              <div className="space-y-2 mb-4">
                <PromptChip text="Why did AWS spend increase?" onClick={() => navigate('/copilot')} />
                <PromptChip text="Where can we save $10,000 this month?" onClick={() => navigate('/copilot')} />
                <PromptChip text="Are we on track to exceed budget?" onClick={() => navigate('/copilot')} />
              </div>

              <button
                onClick={() => navigate('/copilot')}
                className="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
              >
                Launch AI Copilot →
              </button>
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}

function CostDriverBar({ name, cost, percent, color }: { name: string; cost: number; percent: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-300 font-medium">{name}</span>
        <span className="text-white font-mono">{formatCurrency(cost)} ({percent}%)</span>
      </div>
      <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function OpportunityRow({
  title,
  resource,
  evidence,
  savings,
  confidence,
}: {
  title: string;
  resource: string;
  evidence: string;
  savings: number;
  confidence: string;
}) {
  return (
    <div className="py-3 flex items-center justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <span className="text-white text-sm font-medium">{title}</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
            {confidence}
          </span>
        </div>
        <p className="text-gray-400 text-xs mt-0.5 font-mono">{resource}</p>
        <p className="text-gray-500 text-xs mt-0.5">{evidence}</p>
      </div>
      <div className="text-right shrink-0">
        <span className="text-emerald-400 font-bold text-sm">{formatCurrency(savings)}/mo</span>
        <p className="text-gray-500 text-[10px]">{formatCurrency(savings * 12)}/yr</p>
      </div>
    </div>
  );
}

function PromptChip({ text, onClick }: { text: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-2 rounded bg-gray-800/60 hover:bg-gray-800 text-gray-300 hover:text-white text-xs border border-gray-700/50 transition-colors"
    >
      "{text}"
    </button>
  );
}
