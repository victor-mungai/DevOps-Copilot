import { CheckCircle2 } from 'lucide-react';
import { motion } from 'motion/react';

export function ConnectedStep() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 text-center py-8"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
        className="flex justify-center"
      >
        <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center">
          <CheckCircle2 className="w-12 h-12 text-green-500" />
        </div>
      </motion.div>

      <div>
        <h3 className="text-2xl font-semibold text-white mb-2">
          AWS Account Connected
        </h3>
        <p className="text-gray-400">
          Your AWS account is now integrated with DevOps Copilot.
          <br />
          Monitoring and analysis will begin shortly.
        </p>
      </div>
    </motion.div>
  );
}