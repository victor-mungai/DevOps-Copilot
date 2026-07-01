import { useCallback, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { ProgressRail } from '../components/ProgressRail';
import { ActivityLog } from '../components/ActivityLog';
import { StepCard } from '../components/StepCard';
import { CreateTenantStep } from '../components/CreateTenantStep';
import { DeployStackStep } from '../components/DeployStackStep';
import { VerifyRoleStep } from '../components/VerifyRoleStep';
import { ConnectedStep } from '../components/ConnectedStep';
import { apiFetch, errorMessage } from '../lib/api';
import { formatTime } from '../lib/format';
import { useTenant } from '../lib/tenant';

// The onboarding wizard — now one route within the platform rather than the
// whole app. On success it writes tenant identity to context (persisted) and
// offers a jump straight to the dashboard.

export function OnboardingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { tenantId, accountId, setTenant } = useTenant();

  // `?new=1` (from the workspace selector) forces a fresh wizard to connect an
  // additional account, even when the active workspace is already connected.
  const isNew = searchParams.get('new') === '1';

  // Landing-aware start: fully connected → done; tenant but no AWS → connect
  // step; brand new → create workspace.
  const connected = !isNew && Boolean(accountId);
  const startTenant = isNew ? '' : tenantId;
  const [currentStep, setCurrentStep] = useState(connected ? 4 : startTenant ? 2 : 1);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(
    connected ? new Set([1, 2, 3, 4]) : startTenant ? new Set([1]) : new Set()
  );
  const [logs, setLogs] = useState<string[]>([
    `[${formatTime(new Date())}] Onboarding initialized`,
  ]);

  const addLog = useCallback((message: string) => {
    setLogs((prev) => [...prev, `[${formatTime(new Date())}] ${message}`]);
  }, []);

  const completeStep = useCallback((stepNumber: number) => {
    setCompletedSteps((prev) => new Set([...prev, stepNumber]));
    setCurrentStep(Math.min(stepNumber + 1, 4));
  }, []);

  const handleCreateTenant = useCallback(
    async (tenantName: string) => {
      const data = await apiFetch<{ tenant_id?: string }>('/v1/tenants', {
        method: 'POST',
        body: { name: tenantName },
      });
      const id = String(data.tenant_id || '');
      setTenant({ tenantId: id, tenantName });
      addLog(`Tenant created: ${tenantName}`);
      addLog(`Tenant ID: ${id}`);
      completeStep(1);
    },
    [addLog, completeStep, setTenant]
  );

  const handleDeployStack = useCallback(async () => {
    const id = tenantId.trim();
    if (!id) throw new Error('Tenant ID is required.');
    addLog('Opening stack deployment');
    const data = await apiFetch<{ onboarding_url?: string }>(
      `/v1/tenants/${id}/onboarding-link`,
      { tenantId: id }
    );
    if (data.onboarding_url) window.open(data.onboarding_url, '_blank');
    addLog('Onboarding link opened');
    completeStep(2);
  }, [tenantId, addLog, completeStep]);

  const handleVerifyRole = useCallback(
    async (roleArn: string, region: string, tenantOverride?: string) => {
      const id = (tenantOverride || tenantId).trim();
      if (!id) throw new Error('Tenant ID is required.');
      addLog(`Attempting role verification in ${region || 'default region'}`);
      addLog(`Role ARN: ${roleArn}`);
      const body: { role_arn: string; region?: string } = { role_arn: roleArn };
      if (region) body.region = region;

      const data = await apiFetch<{ account_id?: string }>(`/v1/tenants/${id}/verify`, {
        method: 'POST',
        tenantId: id,
        body,
      });
      if (data.account_id) setTenant({ accountId: String(data.account_id) });
      if (id !== tenantId) setTenant({ tenantId: id });
      addLog('AssumeRole successful');
      addLog('Account verified');
      setCompletedSteps((prev) => new Set([...prev, 3, 4]));
      setCurrentStep(4);
    },
    [tenantId, addLog, setTenant]
  );

  const handleError = useCallback(
    (label: string, error: unknown) => addLog(`${label}: ${errorMessage(error)}`),
    [addLog]
  );

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-start justify-between mb-10 gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Connect your AWS account</h1>
          <p className="text-gray-400 text-sm mt-1">
            Cross-account IAM role onboarding. This is a one-time setup per account.
          </p>
        </div>
        {accountId && (
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium shrink-0"
          >
            Go to Dashboard →
          </button>
        )}
      </div>

      <div className="flex gap-8">
        <ProgressRail currentStep={currentStep} completedSteps={completedSteps} />

        <div className="flex-1 space-y-8">
          <div className="relative min-h-[500px]">
            <StepCard stepNumber={1} currentStep={currentStep} isCompleted={completedSteps.has(1)} totalSteps={4}>
              <CreateTenantStep
                isActive={currentStep === 1}
                isCompleted={completedSteps.has(1)}
                onComplete={handleCreateTenant}
                onError={handleError}
              />
            </StepCard>

            <StepCard stepNumber={2} currentStep={currentStep} isCompleted={completedSteps.has(2)} totalSteps={4}>
              <DeployStackStep
                isActive={currentStep === 2}
                isCompleted={completedSteps.has(2)}
                onComplete={handleDeployStack}
                onError={handleError}
              />
            </StepCard>

            <StepCard stepNumber={3} currentStep={currentStep} isCompleted={completedSteps.has(3)} totalSteps={4}>
              <VerifyRoleStep
                isActive={currentStep === 3}
                isCompleted={completedSteps.has(3)}
                tenantId={tenantId}
                accountId={accountId}
                onTenantIdChange={(id: string) => setTenant({ tenantId: id })}
                onComplete={handleVerifyRole}
                onError={handleError}
              />
            </StepCard>

            <StepCard stepNumber={4} currentStep={currentStep} isCompleted={completedSteps.has(4)} totalSteps={4}>
              <ConnectedStep />
            </StepCard>
          </div>

          <ActivityLog logs={logs} />
        </div>
      </div>
    </div>
  );
}
