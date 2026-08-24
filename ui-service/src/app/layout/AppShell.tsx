import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router';
import {
  LayoutDashboard,
  Server,
  LineChart,
  Lightbulb,
  Bot,
  DollarSign,
  Bell,
  Settings,
  PlugZap,
  LogOut,
  ChevronDown,
} from 'lucide-react';
import type { ComponentType } from 'react';
import { useTenant } from '../lib/tenant';
import { useAuth } from '../lib/auth';
import { WorkspaceSelector } from './WorkspaceSelector';
import { RegionSelector } from './RegionSelector';

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/cost-intelligence', label: 'Cost Intelligence', icon: DollarSign },
  { to: '/infrastructure', label: 'Infrastructure', icon: Server },
  { to: '/metrics', label: 'Metrics', icon: LineChart },
  { to: '/insights', label: 'Insights', icon: Lightbulb },
  { to: '/optimization', label: 'Optimization', icon: PlugZap },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/copilot', label: 'AI Copilot', icon: Bot },
  { to: '/settings', label: 'Settings', icon: Settings },
];

function NavRow({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
          isActive
            ? 'bg-emerald-600/15 text-emerald-300 border border-emerald-600/30'
            : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
        }`
      }
    >
      <Icon className="w-4 h-4 shrink-0" />
      {item.label}
    </NavLink>
  );
}

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { clearTenant } = useTenant();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    clearTenant(); // avoid leaking workspace state to the next user on this device
    navigate('/login', { replace: true });
  };

  const initials = (user?.name || user?.email || '?')
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <div className="min-h-screen bg-[#0B0F17] text-white flex">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 border-r border-gray-800 flex flex-col h-screen sticky top-0">
        <div className="px-5 py-5 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="font-semibold leading-tight">DevOps Copilot</p>
              <p className="text-xs text-gray-500 leading-tight">Cloud Operations</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAV.map((item) => (
            <NavRow key={item.to} item={item} />
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-gray-800">
          <NavLink
            to="/onboarding"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-sky-600/15 text-sky-300 border border-sky-600/30'
                  : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
              }`
            }
          >
            <PlugZap className="w-4 h-4 shrink-0" />
            Connect AWS
          </NavLink>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-gray-800 flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">{titleForPath(location.pathname)}</span>
            <WorkspaceSelector />
            <RegionSelector />
          </div>

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className="flex items-center gap-2 text-sm text-gray-300 hover:text-white"
            >
              <span className="w-7 h-7 rounded-full bg-emerald-600/30 border border-emerald-600/40 flex items-center justify-center text-xs font-medium text-emerald-200">
                {initials}
              </span>
              <span className="hidden sm:block">{user?.name || user?.email}</span>
              <ChevronDown className="w-4 h-4" />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 mt-2 w-56 rounded-lg bg-[#111827] border border-gray-800 shadow-xl z-20 py-1">
                  <div className="px-3 py-2 border-b border-gray-800">
                    <p className="text-sm text-white truncate">{user?.name}</p>
                    <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-white/5 hover:text-white"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              </>
            )}
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-6xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

function titleForPath(path: string): string {
  const map: Record<string, string> = {
    '/': 'Dashboard',
    '/cost-intelligence': 'Cost Intelligence',
    '/infrastructure': 'Infrastructure',
    '/metrics': 'Metrics',
    '/insights': 'Insights',
    '/optimization': 'Optimization',
    '/copilot': 'AI Copilot',
    '/cost': 'Cost Optimization',
    '/alerts': 'Alerts',
    '/settings': 'Settings',
    '/onboarding': 'Connect AWS',
  };
  return map[path] ?? '';
}
