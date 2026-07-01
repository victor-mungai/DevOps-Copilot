import type { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

// Reusable dashboard building blocks, styled to match the existing dark theme
// (bg #0B0F17 / panels #111827 / border gray-800).

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-8 gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-gray-400 text-sm mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

export function Panel({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl bg-[#111827] border border-gray-800 ${className}`}>{children}</div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  accent = 'text-white',
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  accent?: string;
}) {
  return (
    <Panel className="p-5">
      <p className="text-gray-400 text-xs uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-semibold mt-2 ${accent}`}>{value}</p>
      {hint && <p className="text-gray-500 text-xs mt-1">{hint}</p>}
    </Panel>
  );
}

const SEVERITY_STYLES: Record<string, string> = {
  high: 'bg-red-500/15 text-red-400 border-red-500/30',
  critical: 'bg-red-500/15 text-red-400 border-red-500/30',
  medium: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  warning: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  low: 'bg-sky-500/15 text-sky-400 border-sky-500/30',
  healthy: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  // Alert statuses
  open: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  acknowledged: 'bg-sky-500/15 text-sky-400 border-sky-500/30',
  resolved: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  // Inventory "has insight" flag
  insight: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
};

export function SeverityBadge({ value }: { value: string }) {
  const style = SEVERITY_STYLES[value?.toLowerCase()] ?? 'bg-gray-700/40 text-gray-300 border-gray-600';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${style}`}>
      {value}
    </span>
  );
}

export function EmptyState({
  title,
  description,
  icon,
  action,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Panel className="p-12 flex flex-col items-center text-center">
      {icon && <div className="text-gray-600 mb-4">{icon}</div>}
      <p className="text-white font-medium">{title}</p>
      {description && <p className="text-gray-500 text-sm mt-1 max-w-md">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </Panel>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-gray-400 text-sm">
      <Loader2 className="w-4 h-4 animate-spin" />
      {label ?? 'Loading…'}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm px-4 py-3 mb-4">
      {message}
    </div>
  );
}
