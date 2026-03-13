import { useState, useCallback } from 'react';
import { ProgressRail } from './components/ProgressRail';
import { ActivityLog } from './components/ActivityLog';
import { StepCard } from './components/StepCard';
import { CreateTenantStep } from './components/CreateTenantStep';
import { DeployStackStep } from './components/DeployStackStep';
import { VerifyRoleStep } from './components/VerifyRoleStep';
import { ConnectedStep } from './components/ConnectedStep';

export default function App() {
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [logs, setLogs] = useState<string[]>([
    `[${formatTime(new Date())}] Onboarding initialized`,
  ]);
  const [tenantId, setTenantId] = useState('');
  const [accountId, setAccountId] = useState('');

  const apiBase = import.meta.env.VITE_API_BASE || window.location.origin;

  const addLog = useCallback((message: string) => {
    setLogs((prev) => [...prev, `[${formatTime(new Date())}] ${message}`]);
  }, []);

  const completeStep = useCallback((stepNumber: number) => {
    setCompletedSteps((prev) => new Set([...prev, stepNumber]));
    setCurrentStep(Math.min(stepNumber + 1, 4));
  }, []);

  const readJson = useCallback(async (res: Response) => {
    const raw = await res.text();
    if (!raw) return {};
    try {
      return JSON.parse(raw);
    } catch {
      return { detail: raw };
    }
  }, []);

  const formatError = useCallback((error: unknown) => {
    if (typeof error === 'string') return error;
    if (error instanceof Error) return error.message;
    try {
      return JSON.stringify(error);
    } catch {
      return 'Unknown error';
    }
  }, []);

  const handleCreateTenant = useCallback(
    async (tenantName: string) => {
      const res = await fetch(`${apiBase}/v1/tenants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: tenantName }),
      });
      const data = await readJson(res);
      if (!res.ok) {
        throw data;
      }
      const id = String(data.tenant_id || '');
      setTenantId(id);
      addLog(`Tenant created: ${tenantName}`);
      addLog(`Tenant ID: ${id}`);
      completeStep(1);
    },
    [apiBase, addLog, completeStep, readJson]
  );

  const handleDeployStack = useCallback(async () => {
    const id = tenantId.trim();
    if (!id) {
      throw new Error('Tenant ID is required.');
    }
    addLog('Opening stack deployment');
    const res = await fetch(`${apiBase}/v1/tenants/${id}/onboarding-link`);
    const data = await readJson(res);
    if (!res.ok) {
      throw data;
    }
    if (data.onboarding_url) {
      window.open(data.onboarding_url, '_blank');
    }
    addLog('Onboarding link opened');
    completeStep(2);
  }, [apiBase, tenantId, addLog, completeStep, readJson]);

  const handleVerifyRole = useCallback(
    async (roleArn: string, region: string, tenantOverride?: string) => {
      const id = (tenantOverride || tenantId).trim();
      if (!id) {
        throw new Error('Tenant ID is required.');
      }
      addLog(`Attempting role verification in ${region || 'default region'}`);
      addLog(`Role ARN: ${roleArn}`);
      const payload: { role_arn: string; region?: string } = {
        role_arn: roleArn,
      };
      if (region) {
        payload.region = region;
      }

      const res = await fetch(`${apiBase}/v1/tenants/${id}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await readJson(res);
      if (!res.ok) {
        throw data;
      }
      if (data.account_id) {
        setAccountId(String(data.account_id));
      }
      addLog('AssumeRole successful');
      addLog('Account verified');
      setCompletedSteps((prev) => new Set([...prev, 3, 4]));
      setCurrentStep(4);
    },
    [apiBase, tenantId, addLog, readJson]
  );

  const handleError = useCallback(
    (label: string, error: unknown) => {
      addLog(`${label}: ${formatError(error)}`);
    },
    [addLog, formatError]
  );

  return (
    <div className="min-h-screen bg-[#0B0F17] flex">
      {/* Progress Rail */}
      <ProgressRail currentStep={currentStep} completedSteps={completedSteps} />

      {/* Main Content */}
      <div className="flex-1 p-12 overflow-y-auto">
        <div className="max-w-3xl mx-auto space-y-8">
          {/* Header */}
          <div className="mb-12">
            <h1 className="text-3xl font-semibold text-white mb-2">
              DevOps Copilot AWS Onboarding
            </h1>
            <p className="text-gray-400">
              Connect your AWS account to enable monitoring and automation.
            </p>
          </div>

          {/* Step Cards - Stacked Layout */}
          <div className="relative min-h-[500px] mb-12">
            {/* Step 1: Create Tenant */}
            <StepCard
              stepNumber={1}
              currentStep={currentStep}
              isCompleted={completedSteps.has(1)}
              totalSteps={4}
            >
              <CreateTenantStep
                isActive={currentStep === 1}
                isCompleted={completedSteps.has(1)}
                onComplete={handleCreateTenant}
                onError={handleError}
              />
            </StepCard>

            {/* Step 2: Deploy Stack */}
            <StepCard
              stepNumber={2}
              currentStep={currentStep}
              isCompleted={completedSteps.has(2)}
              totalSteps={4}
            >
              <DeployStackStep
                isActive={currentStep === 2}
                isCompleted={completedSteps.has(2)}
                onComplete={handleDeployStack}
                onError={handleError}
              />
            </StepCard>

            {/* Step 3: Verify Role */}
            <StepCard
              stepNumber={3}
              currentStep={currentStep}
              isCompleted={completedSteps.has(3)}
              totalSteps={4}
            >
              <VerifyRoleStep
                isActive={currentStep === 3}
                isCompleted={completedSteps.has(3)}
                tenantId={tenantId}
                accountId={accountId}
                onTenantIdChange={setTenantId}
                onComplete={handleVerifyRole}
                onError={handleError}
              />
            </StepCard>

            {/* Step 4: Connected */}
            <StepCard
              stepNumber={4}
              currentStep={currentStep}
              isCompleted={completedSteps.has(4)}
              totalSteps={4}
            >
              <ConnectedStep />
            </StepCard>
          </div>

          {/* Activity Log */}
          <ActivityLog logs={logs} />
        </div>
      </div>
    </div>
  );
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
