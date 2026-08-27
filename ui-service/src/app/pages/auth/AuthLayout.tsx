import type { ReactNode } from 'react';
import { Bot } from 'lucide-react';

// Centered card shell shared by Login and Register.
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#0B0F17] text-white flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-8 h-8 rounded bg-emerald-600 font-bold text-white text-xs tracking-wider mb-3">
            DC
          </div>
          <h2 className="text-sm font-semibold tracking-wider uppercase text-gray-300">DEVOPS COPILOT</h2>
        </div>

        <div className="rounded-xl bg-[#111827] border border-gray-800 p-6 shadow-lg">
          <h1 className="text-lg font-semibold text-white">{title}</h1>
          <p className="text-gray-400 text-xs mt-1 mb-6">{subtitle}</p>
          {children}
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">{footer}</p>
      </div>
    </div>
  );
}

export function AuthField({
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  autoComplete,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoComplete?: string;
}) {
  return (
    <label className="block mb-4">
      <span className="text-sm text-gray-300">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className="mt-1.5 w-full px-3 py-2.5 rounded-lg bg-[#0B0F17] border border-gray-700 text-white text-sm focus:outline-none focus:border-emerald-500"
      />
    </label>
  );
}
