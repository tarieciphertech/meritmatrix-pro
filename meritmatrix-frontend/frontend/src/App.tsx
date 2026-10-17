// Application root: auth + school providers, route definitions, and protected-route wrapper.
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/auth';
import { SchoolProvider } from './lib/school-context';
import AppLayout from './layouts/AppLayout';
import LoginPage from './pages/LoginPage';
import ChangePasswordPage from './pages/ChangePasswordPage';
import GuardianActivationPage from './pages/GuardianActivationPage';
import DashboardPage from './pages/DashboardPage';
import SchoolsPage from './pages/SchoolsPage';
import SchoolConfigurationPage from './pages/SchoolConfigurationPage';
import SchoolCalendarPage from './pages/SchoolCalendarPage';
import TeachingAssignmentsPage from './pages/TeachingAssignmentsPage';
import AttendancePage from './pages/AttendancePage';
import StudentsPage from './pages/StudentsPage';
import GuardiansPage from './pages/GuardiansPage';
import GuardianPortalPage from './pages/GuardianPortalPage';
import StaffPage from './pages/StaffPage';
import EnrollmentsPage from './pages/EnrollmentsPage';
import AcademicSetupPage from './pages/AcademicSetupPage';
import AssessmentsPage from './pages/AssessmentsPage';
import FeesPage from './pages/FeesPage';
import ReportCardsPage from './pages/ReportCardsPage';
import AuditLogsPage from './pages/AuditLogsPage';
import { Spinner } from './components/ui';
import type { ReactNode } from 'react';

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, initializing } = useAuth();
  const location = useLocation();
  if (initializing) return <div className="flex min-h-screen items-center justify-center bg-slate-50"><Spinner label="Loading…" /></div>;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  const mustChangePassword = Boolean(user.must_change_password);
  if (mustChangePassword && location.pathname !== '/change-password') return <Navigate to="/change-password" replace />;
  if (!mustChangePassword && location.pathname === '/change-password') return <Navigate to="/" replace />;
  const isGuardian = (user.roles ?? []).some((role) => role.name === 'GUARDIAN');
  if (isGuardian && location.pathname !== '/guardian-portal') return <Navigate to="/guardian-portal" replace />;
  return <>{children}</>;
}

export default function App() {
  return <AuthProvider><SchoolProvider><Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/activate-guardian" element={<GuardianActivationPage />} />
    <Route path="/change-password" element={<RequireAuth><ChangePasswordPage /></RequireAuth>} />
    <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/schools" element={<SchoolsPage />} />
      <Route path="/school-configuration" element={<SchoolConfigurationPage />} />
      <Route path="/school-calendar" element={<SchoolCalendarPage />} />
      <Route path="/teaching-assignments" element={<TeachingAssignmentsPage />} />
      <Route path="/attendance" element={<AttendancePage />} />
      <Route path="/students" element={<StudentsPage />} />
      <Route path="/guardians" element={<GuardiansPage />} />
      <Route path="/guardian-portal" element={<GuardianPortalPage />} />
      <Route path="/staff" element={<StaffPage />} />
      <Route path="/enrollments" element={<EnrollmentsPage />} />
      <Route path="/academic-setup" element={<AcademicSetupPage />} />
      <Route path="/assessments" element={<AssessmentsPage />} />
      <Route path="/fees" element={<FeesPage />} />
      <Route path="/report-cards" element={<ReportCardsPage />} />
      <Route path="/audit-logs" element={<AuditLogsPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></SchoolProvider></AuthProvider>;
}
