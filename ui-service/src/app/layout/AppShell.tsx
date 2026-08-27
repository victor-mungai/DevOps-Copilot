import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router';
import {
  LayoutDashboard,
  Server,
  LineChart,
  Lightbulb,
  Bot,
  DollarSign,
  PiggyBank,
  Settings,
  PlugZap,
  LogOut,
  ChevronDown,
} from 'lucide-react';
import type { ComponentType } from 'react';
import { useTenant } from '../lib/tenant';
import { useAuth } from '../lib/auth';
import { WorkspaceSelector } from './WorkspaceSelector';
import { TimePeriodSelector } from './TimePeriodSelector';
import { RegionSelector } from './RegionSelector';

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

const NAV: NavItem[] = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/cost-intelligence', label: 'Cost', icon: DollarSign },
  { to: '/infrastructure', label: 'Infrastructure', icon: Server },
  { to: '/metrics', label: 'Metrics', icon: LineChart },
  { to: '/insights', label: 'Insights', icon: Lightbulb },
  { to: '/savings', label: 'Savings', icon: PiggyBank },
  { to: '/copilot', label: 'Copilot', icon: Bot },
];

function NavRow({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-emerald-600/15 text-emerald-400 border border-emerald-600/30'
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
  const { clearTenant, isConnected, accountId, scopeLabel } = useTenant();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    clearTenant();
    navigate('/login', { replace: true });
  };

  const initials = (user?.name || user?.email || '?')
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <div className="min-h-screen bg-[#0B0F17] text-white flex font-sans">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 border-r border-gray-800 flex flex-col h-screen sticky top-0 bg-[#0B0F17]">
        <div className="px-5 py-4 border-b border-gray-800">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-emerald-600 flex items-center justify-center font-bold text-white text-xs tracking-wider">
              DC
            </div>
            <div>
              <p className="font-semibold text-sm tracking-wide text-white">DEVOPS COPILOT</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAV.map((item) => (
            <NavRow key={item.to} item={item} />
          ))}

          <div className="pt-4 pb-2 px-3">
            <div className="h-px bg-gray-800 mb-4" />
            <p className="text-[11px] font-semibold tracking-wider text-gray-500 uppercase mb-2">Workspace</p>
            <NavLink
              to="/settings"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-600/15 text-emerald-400 border border-emerald-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
                }`
              }
            >
              <Settings className="w-4 h-4 shrink-0" />
              Settings
            </NavLink>
          </div>
        </nav>

        <div className="px-4 py-3 border-t border-gray-800">
          {isConnected ? (
            <div className="flex items-center gap-2 text-xs text-gray-300">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
              <span className="font-medium text-gray-300">AWS Connected</span>
              {accountId && <span className="text-gray-500 text-[11px] truncate">({accountId})</span>}
            </div>
          ) : (
            <button
              onClick={() => navigate('/onboarding')}
              className="w-full flex items-center justify-between px-3 py-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-medium hover:bg-amber-500/20"
            >
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                Connect AWS
              </span>
              <PlugZap className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-gray-800 flex items-center justify-between px-8 shrink-0 bg-[#0B0F17]">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-semibold text-white mr-1">{titleForPath(location.pathname)}</span>
            <WorkspaceSelector />
            <TimePeriodSelector />
            <RegionSelector />
          </div>

          {/* User menu & Scope Indicator */}
          <div className="flex items-center gap-4">
            <span className="hidden md:inline-block px-2.5 py-1 rounded bg-gray-900 border border-gray-800 text-[11px] font-mono text-gray-400">
              {scopeLabel}
            </span>

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
    '/': 'Overview',
    '/cost-intelligence': 'Cost Intelligence',
    '/infrastructure': 'Infrastructure',
    '/metrics': 'Metrics',
    '/insights': 'Insights',
    '/savings': 'Savings',
    '/copilot': 'Copilot',
    '/settings': 'Settings',
    '/onboarding': 'Connect AWS',
  };
  return map[path] ?? '';
}
