import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { AuthProvider } from './lib/auth';
import { TenantProvider } from './lib/tenant';
import { RequireAuth, DashboardLanding } from './layout/guards';
import { AppShell } from './layout/AppShell';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { InfrastructurePage } from './pages/InfrastructurePage';
import { MetricsPage } from './pages/MetricsPage';
import { InsightsPage } from './pages/InsightsPage';
import { CopilotPage } from './pages/CopilotPage';
import { CostPage } from './pages/CostPage';
import { AlertsPage } from './pages/AlertsPage';
import { SettingsPage } from './pages/SettingsPage';
import { OnboardingPage } from './pages/OnboardingPage';

export default function App() {
  return (
    <AuthProvider>
      <TenantProvider>
        <BrowserRouter>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected */}
            <Route element={<RequireAuth />}>
              <Route element={<AppShell />}>
                <Route index element={<DashboardLanding />} />
                <Route path="infrastructure" element={<InfrastructurePage />} />
                <Route path="metrics" element={<MetricsPage />} />
                <Route path="insights" element={<InsightsPage />} />
                <Route path="copilot" element={<CopilotPage />} />
                <Route path="cost" element={<CostPage />} />
                <Route path="alerts" element={<AlertsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="onboarding" element={<OnboardingPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </TenantProvider>
    </AuthProvider>
  );
}
