import { ReactNode } from 'react';
import { motion, AnimatePresence } from 'motion/react';

interface StepCardProps {
  stepNumber: number;
  currentStep: number;
  isCompleted: boolean;
  totalSteps: number;
  children: ReactNode;
}

export function StepCard({ 
  stepNumber, 
  currentStep, 
  isCompleted, 
  totalSteps,
  children 
}: StepCardProps) {
  const isActive = currentStep === stepNumber;
  const isPast = currentStep > stepNumber;
  const isFuture = currentStep < stepNumber;
  
  // Don't render future steps
  if (isFuture) return null;
  
  // Calculate scale and position based on how far back this card is
  const offset = currentStep - stepNumber;
  const scale = 1 - (offset * 0.05);
  const yOffset = offset * 25;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ 
          opacity: isActive ? 1 : 0.4,
          y: 0,
          scale: scale,
          zIndex: totalSteps - offset,
        }}
        exit={{ opacity: 0, y: -50 }}
        transition={{ 
          duration: 0.5,
          ease: [0.4, 0, 0.2, 1]
        }}
        className="absolute w-full"
        style={{
          top: `${yOffset}px`,
          pointerEvents: isActive ? 'auto' : 'none',
        }}
      >
        {/* Outer glow - only visible when active */}
        <motion.div 
          animate={{
            opacity: isActive ? 0.75 : 0,
          }}
          transition={{ duration: 0.5 }}
          className="absolute -inset-[10px] -z-20"
          style={{
            background: `
              radial-gradient(circle at 0% 0%, hsl(27deg 93% 60%), transparent),
              radial-gradient(circle at 100% 0%, #00a6ff, transparent),
              radial-gradient(circle at 0% 100%, #ff0056, transparent),
              radial-gradient(circle at 100% 100%, #6500ff, transparent)
            `,
            filter: 'blur(20px)',
            animation: isActive ? 'pulse 3s ease-in-out infinite' : 'none',
          }}
        />
        
        {/* Inner glow border */}
        <div 
          className="absolute -inset-[2px] -z-10 rounded-lg"
          style={{
            background: `
              radial-gradient(circle at 0% 0%, hsl(27deg 93% 60%), transparent),
              radial-gradient(circle at 100% 0%, #00a6ff, transparent),
              radial-gradient(circle at 0% 100%, #ff0056, transparent),
              radial-gradient(circle at 100% 100%, #6500ff, transparent)
            `,
          }}
        />
        
        {/* Main card */}
        <motion.div
          animate={{
            background: isCompleted 
              ? 'linear-gradient(135deg, #1a1a22 10%, #050505 60%)'
              : isActive
              ? 'linear-gradient(135deg, #1e1e24 10%, #0a0a0f 60%)'
              : 'linear-gradient(135deg, #15151a 10%, #050505 60%)',
          }}
          transition={{ duration: 0.3 }}
          className="relative rounded-lg p-6 min-h-[200px]"
          style={{
            backgroundSize: '200% 200%',
            animation: isActive ? 'gradientShift 5s ease-in-out infinite' : 'none',
          }}
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            {children}
          </motion.div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}