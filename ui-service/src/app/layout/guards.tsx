import { Navigate, Outlet, useLocation } from 'react-router';
import { useAuth } from '../lib/auth';
import { useTenant } from '../lib/tenant';
import { DashboardPage } from '../pages/DashboardPage';

// Blocks every app route for unauthenticated users → /login.
export function RequireAuth() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

// Landing logic for the index route:
//   no tenant            → create workspace (onboarding)
//   tenant, no AWS yet   → connect AWS (onboarding)
//   tenant + AWS         → dashboard
export function DashboardLanding() {
  const { tenantId, accountId } = useTenant();
  if (!tenantId || !accountId) {
    return <Navigate to="/onboarding" replace />;
  }
  return <DashboardPage />;
}
