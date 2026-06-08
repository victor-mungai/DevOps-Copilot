import { useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

interface CreateTenantStepProps {
  isCompleted: boolean;
  isActive: boolean;
  onComplete: (tenantName: string) => Promise<void>;
  onError: (label: string, error: unknown) => void;
}

export function CreateTenantStep({
  isCompleted,
  isActive,
  onComplete,
  onError,
}: CreateTenantStepProps) {
  const [tenantName, setTenantName] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!tenantName.trim() || !isActive) return;
    setLoading(true);
    try {
      await onComplete(tenantName);
    } catch (error) {
      onError('Create tenant failed', error);
    } finally {
      setLoading(false);
    }
  };

  if (isCompleted) {
    return (
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
          <Check className="w-3 h-3 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Create Tenant</h3>
          <p className="text-sm text-green-400 mt-1">
            ✓ Tenant created successfully
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
        <h3 className="text-lg font-semibold text-white">Create Tenant</h3>
        <p className="text-sm text-gray-400 mt-1">
          Create a workspace for this AWS account.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="tenant-name" className="text-gray-300">
          Tenant Name
        </Label>
        <Input
          id="tenant-name"
          value={tenantName}
          onChange={(e) => setTenantName(e.target.value)}
          placeholder="my-aws-workspace"
          className="bg-[#0B0F17] border-gray-700 text-white"
          disabled={loading || !isActive}
          onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
        />
      </div>

      <Button
        onClick={handleCreate}
        disabled={!tenantName.trim() || loading || !isActive}
        className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-900/30 transition-all hover:shadow-blue-900/50"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Creating...
          </>
        ) : (
          'Create Tenant'
        )}
      </Button>
    </div>
  );
}

