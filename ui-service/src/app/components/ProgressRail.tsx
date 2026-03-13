import { Check } from 'lucide-react';
import { motion } from 'motion/react';

interface Step {
  id: number;
  label: string;
}

interface ProgressRailProps {
  currentStep: number;
  completedSteps: Set<number>;
}

const steps: Step[] = [
  { id: 1, label: 'Create Tenant' },
  { id: 2, label: 'Deploy AWS Stack' },
  { id: 3, label: 'Verify Role' },
  { id: 4, label: 'Connected' },
];

export function ProgressRail({ currentStep, completedSteps }: ProgressRailProps) {
  return (
    <div className="w-64 bg-[#0B0F17] border-r border-gray-800 p-8 flex flex-col gap-8">
      {steps.map((step, index) => {
        const isCompleted = completedSteps.has(step.id);
        const isActive = currentStep === step.id;
        const isPending = !isCompleted && !isActive;

        return (
          <div key={step.id} className="flex items-start gap-4">
            {/* Step indicator */}
            <div className="relative flex-shrink-0">
              <motion.div
                initial={false}
                animate={{
                  scale: isActive ? 1.1 : 1,
                  backgroundColor: isCompleted
                    ? '#10B981'
                    : isActive
                    ? '#2563EB'
                    : '#374151',
                }}
                transition={{ duration: 0.3 }}
                className="w-8 h-8 rounded-full flex items-center justify-center"
              >
                {isCompleted ? (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Check className="w-5 h-5 text-white" />
                  </motion.div>
                ) : (
                  <span
                    className={`text-sm font-medium ${
                      isActive ? 'text-white' : 'text-gray-400'
                    }`}
                  >
                    {step.id}
                  </span>
                )}
              </motion.div>
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="absolute left-1/2 top-8 w-0.5 h-8 -ml-px bg-gray-800" />
              )}
            </div>
            {/* Step label */}
            <div className="pt-1">
              <motion.p
                animate={{
                  color: isCompleted || isActive ? '#fff' : '#9CA3AF',
                  fontWeight: isActive ? 600 : 400,
                }}
                className="text-sm"
              >
                {step.label}
              </motion.p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
