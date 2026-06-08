import { useEffect, useRef } from 'react';
import { motion } from 'motion/react';

interface ActivityLogProps {
  logs: string[];
}

export function ActivityLog({ logs }: ActivityLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-[#111827] border border-gray-800 rounded-lg p-4 h-64 overflow-hidden"
    >
      <div className="mb-2 text-xs text-gray-400 font-medium uppercase tracking-wide">
        Activity Log
      </div>
      <div
        ref={scrollRef}
        className="h-[calc(100%-2rem)] overflow-y-auto font-mono text-sm text-gray-300 space-y-1"
      >
        {logs.map((log, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            className="whitespace-nowrap"
          >
            {log}
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
