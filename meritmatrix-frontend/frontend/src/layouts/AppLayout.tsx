// Authenticated application shell: sidebar navigation (responsive), header
// with school selector and user menu, and the routed content outlet.

import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { useSchool } from '../lib/school-context';
import { Select } from '../components/ui';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/schools', label: 'Schools' },
  { to: '/students', label: 'Students' },
  { to: '/guardians', label: 'Guardians' },
  { to: '/staff', label: 'Staff' },
  { to: '/enrollments', label: 'Enrollments' },
];

function navClasses({ isActive }: { isActive: boolean }) {
  return `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? 'bg-indigo-50 text-indigo-700'
      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`;
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { schools, selectedSchool, selectSchool } = useSchool();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  const sidebar = (
    <nav className="space-y-1 px-3 py-4">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={navClasses}
          onClick={() => setMobileOpen(false)}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 border-r border-slate-200 bg-white lg:block">
        <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">
            M
          </div>
          <span className="text-sm font-semibold text-slate-900">MeritMatrix Pro</span>
        </div>
        {sidebar}
      </aside>

      {/* Mobile sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="fixed inset-0 bg-slate-900/50" onClick={() => setMobileOpen(false)} />
          <aside className="fixed inset-y-0 left-0 w-60 bg-white shadow-xl">
            <div className="flex h-14 items-center justify-between border-b border-slate-200 px-4">
              <span className="text-sm font-semibold text-slate-900">MeritMatrix Pro</span>
              <button
                type="button"
                className="rounded-md p-1 text-slate-400 hover:text-slate-600"
                onClick={() => setMobileOpen(false)}
                aria-label="Close menu"
              >
                ✕
              </button>
            </div>
            {sidebar}
          </aside>
        </div>
      )}

      {/* Main column */}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M2 4.75A.75.75 0 0 1 2.75 4h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 4.75Zm0 10.5a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75ZM2 10a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 10Z"
                  clipRule="evenodd"
                />
              </svg>
            </button>

            {/* School selector — drives all school-scoped screens */}
            <div className="flex items-center gap-2">
              <span className="hidden text-xs font-medium uppercase tracking-wide text-slate-400 sm:inline">
                School
              </span>
              <Select
                aria-label="Select school"
                className="!w-auto min-w-40 max-w-64"
                value={selectedSchool?.id ?? ''}
                onChange={(e) => selectSchool(e.target.value)}
              >
                <option value="">
                  {schools.length === 0 ? 'No schools available' : 'Select a school…'}
                </option>
                {schools.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {user && (
              <div className="hidden text-right sm:block">
                <p className="text-sm font-medium text-slate-800">
                  {user.first_name} {user.last_name}
                </p>
                <p className="text-xs text-slate-500">
                  {user.roles.map((r) => r.name).join(', ') || 'No roles'}
                </p>
              </div>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-inset ring-slate-300 hover:bg-slate-50"
            >
              Sign out
            </button>
          </div>
        </header>

        <main className="p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}