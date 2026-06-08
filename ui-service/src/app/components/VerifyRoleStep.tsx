import { useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

interface VerifyRoleStepProps {
  isCompleted: boolean;
  isActive: boolean;
  tenantId: string;
  accountId: string;
  onTenantIdChange: (tenantId: string) => void;
  onComplete: (roleArn: string, region: string, tenantId: string) => Promise<void>;
  onError: (label: string, error: unknown) => void;
}

export function VerifyRoleStep({
  isCompleted,
  isActive,
  tenantId,
  accountId,
  onTenantIdChange,
  onComplete,
  onError,
}: VerifyRoleStepProps) {
  const [roleArn, setRoleArn] = useState('');
  const [region, setRegion] = useState('us-east-1');
  const [verifying, setVerifying] = useState(false);

  const handleVerify = async () => {
    if (!roleArn.trim() || !isActive) return;
    setVerifying(true);
    try {
      await onComplete(roleArn, region, tenantId);
    } catch (error) {
      onError('Verify role failed', error);
    } finally {
      setVerifying(false);
    }
  };

  if (isCompleted) {
    return (
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
          <Check className="w-3 h-3 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Verify AWS Role</h3>
          <p className="text-sm text-green-400 mt-1">
            ✓ AWS account verified
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`space-y-4 ${
        !isActive ? 'opacity-50 pointer-events-none' : ''
      }`}
    >
      <div>
        <h3 className="text-lg font-semibold text-white">Verify AWS Role</h3>
        <p className="text-sm text-gray-400 mt-1">
          Verify the IAM role for DevOps Copilot integration.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="tenant-id" className="text-gray-300">
            Tenant ID
          </Label>
          <Input
            id="tenant-id"
            value={tenantId}
            onChange={(e) => onTenantIdChange(e.target.value)}
            className="bg-[#0B0F17] border-gray-700 text-white"
            disabled={verifying || !isActive}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="account-id" className="text-gray-300">
            Account ID
          </Label>
          <Input
            id="account-id"
            value={accountId || ''}
            readOnly
            className="bg-[#0B0F17] border-gray-700 text-gray-400"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="role-arn" className="text-gray-300">
          Role ARN
        </Label>
        <Input
          id="role-arn"
          value={roleArn}
          onChange={(e) => setRoleArn(e.target.value)}
          placeholder="arn:aws:iam::123456789012:role/DevOpsCopilotRole"
          className="bg-[#0B0F17] border-gray-700 text-white"
          disabled={verifying || !isActive}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="region" className="text-gray-300">
          Region (optional)
        </Label>
        <Input
          id="region"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          placeholder="us-east-1"
          className="bg-[#0B0F17] border-gray-700 text-white"
          disabled={verifying || !isActive}
        />
      </div>

      <Button
        onClick={handleVerify}
        disabled={!roleArn.trim() || verifying || !isActive}
        className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-900/30 transition-all hover:shadow-blue-900/50"
      >
        {verifying ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Verifying...
          </>
        ) : (
          'Verify Connection'
        )}
      </Button>

      {verifying && (
        <div className="flex items-center gap-2 text-sm text-yellow-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          Attempting role assumption...
        </div>
      )}
    </div>
  );
}

