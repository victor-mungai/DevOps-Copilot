import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { CheckCircle2, ShieldCheck, RefreshCw, ArrowRight, AlertCircle, ExternalLink } from 'lucide-react';
import { ApiError, apiBase, apiFetch, errorMessage } from '../lib/api';
import { AWS_REGIONS, useTenant } from '../lib/tenant';

export function OnboardingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { tenantId, accountId, region, setTenant, setRegion, clearTenant } = useTenant();

  const isNew = searchParams.get('new') === '1';
  const [workspaceName, setWorkspaceName] = useState('');
  const [roleArn, setRoleArn] = useState('');
  const [step, setStep] = useState<'create' | 'connect' | 'verify' | 'success'>(
    accountId && !isNew ? 'success' : tenantId ? 'connect' : 'create'
  );

  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');
  const [verifiedAccount, setVerifiedAccount] = useState(accountId || '');

  // Step 1: Create Workspace
  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceName.trim()) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch<{ tenant_id?: string }>('/v1/tenants', {
        method: 'POST',
        body: { name: workspaceName.trim() },
      });
      const id = String(data.tenant_id || '');
      setTenant({ tenantId: id, tenantName: workspaceName.trim() });
      setStep('connect');
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        clearTenant();
        setStep('create');
        setError('This workspace no longer exists. Create a new workspace to connect an AWS account.');
        return;
      }
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Connect AWS (CloudFormation)
  const handleConnectAWS = async () => {
    if (!tenantId) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch<{ onboarding_url?: string }>(
        `/v1/tenants/${tenantId}/onboarding-link`,
        { tenantId }
      );
      if (data.onboarding_url) {
        window.open(data.onboarding_url, '_blank');
      }
      setStep('verify');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Verify AWS IAM Role connection
  const handleVerifyConnection = useCallback(async () => {
    if (!tenantId) return;
    setVerifying(true);
    setError('');
    try {
      if (!roleArn.trim()) {
        setError('Enter the IAM role ARN created by the onboarding stack.');
        return;
      }
      if (!region) {
        setError('Choose the AWS region where you want to begin discovery.');
        return;
      }
      const data = await apiFetch<{ account_id?: string; account_alias?: string }>(
        `/v1/tenants/${tenantId}/verify`,
        {
          method: 'POST',
          tenantId,
          body: { role_arn: roleArn.trim(), region },
        }
      );
      const verified = String(data.account_id || '');
      if (!verified) throw new Error('AWS did not return an account id');
      setVerifiedAccount(verified);
      setTenant({ tenantId, accountId: verified, tenantName: workspaceName || 'AWS Workspace' });

      // Refresh workspaces list & set newly created workspace active
      fetch(`${apiBase}/v1/tenants/connected`)
        .then((res) => res.json())
        .then(() => {})
        .catch(() => {});

      setStep('success');
    } catch (_) {
      setError(
        "We couldn't verify the connection. The AWS role was created, but we couldn't assume it yet."
      );
    } finally {
      setVerifying(false);
    }
  }, [tenantId, region, workspaceName, roleArn, setTenant, clearTenant]);

  useEffect(() => {
    if (step === 'verify') {
      const timer = setTimeout(() => {
        void handleVerifyConnection();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [step, handleVerifyConnection]);

  if (step === 'success') {
    return (
      <div className="max-w-xl mx-auto py-12">
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-8 shadow-lg text-center">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto mb-4 text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-semibold text-white">AWS Connected</h1>
          <p className="text-gray-400 text-sm mt-1 mb-6">
            Your AWS environment is now actively connected and monitored.
          </p>

          <div className="bg-[#0B0F17] rounded-lg border border-gray-800 p-4 mb-6 text-left space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Account</span>
              <span className="text-white font-mono">{verifiedAccount || accountId || 'No data available'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Region</span>
              <span className="text-white font-mono">{region || 'No data available'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Status</span>
              <span className="text-emerald-400 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Verified
              </span>
            </div>
          </div>

          <button
            onClick={() => navigate('/')}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium"
          >
            Continue to dashboard
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  if (step === 'verify') {
    return (
      <div className="max-w-xl mx-auto py-12">
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-8 shadow-lg">
          <h1 className="text-xl font-semibold text-white mb-1">Connect AWS</h1>
          <p className="text-gray-400 text-sm mb-6">Waiting for AWS connection…</p>

          {error ? (
            <div className="mb-6 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm space-y-3">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
                <div>
                  <p className="font-medium text-white">Connection Pending</p>
                  <p className="text-xs text-amber-200 mt-1">{error}</p>
                </div>
              </div>
              <div className="pt-2 flex items-center gap-3 border-t border-amber-500/20">
                <button
                  onClick={() => void handleVerifyConnection()}
                  disabled={verifying}
                  className="flex items-center gap-2 px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${verifying ? 'animate-spin' : ''}`} />
                  {verifying ? 'Verifying…' : 'Retry'}
                </button>
                <a
                  href="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create.html"
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-amber-300 hover:underline inline-flex items-center gap-1"
                >
                  View setup instructions <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ) : (
            <div className="space-y-3 mb-8">
              <div className="flex items-center gap-3 text-sm text-gray-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>CloudFormation stack detected</span>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>IAM role detected</span>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-300">
                {verifying ? (
                  <RefreshCw className="w-4 h-4 text-emerald-400 animate-spin shrink-0" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                )}
                <span>Access verified</span>
              </div>
            </div>
          )}

          <div className="bg-[#0B0F17] rounded-lg border border-gray-800 p-4 mb-6 text-left space-y-2 text-sm">
            <label className="block text-xs text-gray-500 uppercase tracking-wider font-semibold">IAM role ARN</label>
            <input
              value={roleArn}
              onChange={(event) => setRoleArn(event.target.value)}
              placeholder="arn:aws:iam::<account-id>:role/<role-name>"
              className="w-full px-3 py-2 rounded-lg bg-[#111827] border border-gray-700 text-gray-200 text-xs font-mono focus:outline-none focus:border-emerald-500"
            />
            <label className="block text-xs text-gray-500 uppercase tracking-wider font-semibold pt-2">Initial discovery region</label>
            <select
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#111827] border border-gray-700 text-gray-200 text-xs focus:outline-none focus:border-emerald-500"
            >
              <option value="">Select an AWS region</option>
              {AWS_REGIONS.map((awsRegion) => (
                <option key={awsRegion} value={awsRegion}>{awsRegion}</option>
              ))}
            </select>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500 uppercase tracking-wider font-semibold">Account</span>
              <span className="text-gray-300 font-mono">{verifiedAccount || accountId || 'No data available'}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500 uppercase tracking-wider font-semibold">Region</span>
              <span className="text-gray-300 font-mono">{region || 'No data available'}</span>
            </div>
          </div>

          <button
            onClick={() => void handleVerifyConnection()}
            disabled={verifying}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50"
          >
            {verifying ? 'Verifying…' : 'Continue to dashboard'}
          </button>
        </div>
      </div>
    );
  }

  if (step === 'connect') {
    return (
      <div className="max-w-xl mx-auto py-12">
        <div className="rounded-xl bg-[#111827] border border-gray-800 p-8 shadow-lg">
          <h1 className="text-xl font-semibold text-white mb-1">Connect AWS</h1>
          <p className="text-gray-400 text-sm mb-6">
            Connect your AWS account to monitor infrastructure, performance and costs.
          </p>

          <div className="rounded-lg bg-[#0B0F17] border border-gray-800 p-5 mb-6 space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              AWS Security Model
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Read-only access</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>No AWS credentials stored</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Access can be revoked at any time</span>
            </div>
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm p-3 mb-4">
              {error}
            </div>
          )}

          <button
            onClick={() => void handleConnectAWS()}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium mb-3"
          >
            {loading ? 'Opening CloudFormation…' : 'Connect AWS'}
          </button>
          <p className="text-center text-xs text-gray-500">Takes about 2 minutes</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto py-12">
      <div className="rounded-xl bg-[#111827] border border-gray-800 p-8 shadow-lg">
        <h1 className="text-xl font-semibold text-white mb-1">Create your workspace</h1>
        <p className="text-gray-400 text-sm mb-6">
          Your workspace is where your AWS environment and cost data will appear.
        </p>

        <form onSubmit={handleCreateWorkspace} className="space-y-4">
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm p-3">
              {error}
            </div>
          )}

          <label className="block">
            <span className="text-sm font-medium text-gray-300">Workspace name</span>
            <input
              type="text"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              placeholder="Acme Technologies"
              required
              className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0B0F17] border border-gray-700 text-white text-sm focus:outline-none focus:border-emerald-500"
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium pt-3"
          >
            {loading ? 'Creating…' : 'Continue'}
          </button>
        </form>
      </div>
    </div>
  );
}
