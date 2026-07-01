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
    <div className="min-h-screen bg-[#0B0F17] text-white flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-semibold">DevOps Copilot</span>
        </div>

        <div className="rounded-2xl bg-[#111827] border border-gray-800 p-8">
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="text-gray-400 text-sm mt-1 mb-6">{subtitle}</p>
          {children}
        </div>

        <p className="text-center text-sm text-gray-400 mt-6">{footer}</p>
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
