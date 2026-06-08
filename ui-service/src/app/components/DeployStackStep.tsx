import { useState } from 'react';
import { Check, ExternalLink, Loader2 } from 'lucide-react';
import { Button } from './ui/button';

interface DeployStackStepProps {
  isCompleted: boolean;
  isActive: boolean;
  onComplete: () => Promise<void>;
  onError: (label: string, error: unknown) => void;
}

export function DeployStackStep({
  isCompleted,
  isActive,
  onComplete,
  onError,
}: DeployStackStepProps) {
  const [checking, setChecking] = useState(false);

  const handleOpenDeployment = () => {
    if (!isActive) return;
    setChecking(true);
    onComplete()
      .catch((error) => {
        onError('Open deployment link failed', error);
      })
      .finally(() => {
        setChecking(false);
      });
  };

  if (isCompleted) {
    return (
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
          <Check className="w-3 h-3 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">
            Deploy AWS Integration Stack
          </h3>
          <p className="text-sm text-green-400 mt-1">
            ✓ Stack successfully deployed
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${!isActive ? 'opacity-50 pointer-events-none' : ''}`}>
      <div>
        <h3 className="text-lg font-semibold text-white">
          Deploy AWS Integration Stack
        </h3>
        <p className="text-sm text-gray-400 mt-1">
          Deploy the DevOps Copilot CloudFormation stack in your AWS account.
        </p>
      </div>

      <Button
        onClick={handleOpenDeployment}
        disabled={checking || !isActive}
        className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-900/30 transition-all hover:shadow-blue-900/50"
      >
        <ExternalLink className="w-4 h-4 mr-2" />
        Open Deployment Link
      </Button>

      {checking && (
        <div className="flex items-center gap-2 text-sm text-yellow-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          Opening deployment link...
        </div>
      )}
    </div>
  );
}

