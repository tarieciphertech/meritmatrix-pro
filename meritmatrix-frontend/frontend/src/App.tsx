// Application root: auth + school providers, route definitions, and
// protected-route wrapper.

import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/auth';
import { SchoolProvider } from './lib/school-context';
import AppLayout from './layouts/AppLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import SchoolsPage from './pages/SchoolsPage';
import StudentsPage from './pages/StudentsPage';
import GuardiansPage from './pages/GuardiansPage';
import GuardianPortalPage from './pages/GuardianPortalPage';
import StaffPage from './pages/StaffPage';
import EnrollmentsPage from './pages/EnrollmentsPage';
import AcademicSetupPage from './pages/AcademicSetupPage';
import { Spinner } from './components/ui';
import type { ReactNode } from 'react';

// Wraps routes that require authentication. Redirects to /login if not
// signed in, preserving the intended destination in location state.
function RequireAuth({ children }: { children: ReactNode }) {
  const { user, initializing } = useAuth();
  const location = useLocation();

  if (initializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Spinner label="Loading…" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <SchoolProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/schools" element={<SchoolsPage />} />
            <Route path="/students" element={<StudentsPage />} />
            <Route path="/guardians" element={<GuardiansPage />} />
            <Route path="/guardian-portal" element={<GuardianPortalPage />} />
            <Route path="/staff" element={<StaffPage />} />
            <Route path="/enrollments" element={<EnrollmentsPage />} />
            <Route path="/academic-setup" element={<AcademicSetupPage />} />
          </Route>

          {/* Catch-all: redirect to dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </SchoolProvider>
    </AuthProvider>
  );
}