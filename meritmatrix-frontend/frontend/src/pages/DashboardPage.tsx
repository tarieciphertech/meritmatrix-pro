// Dashboard: shows the signed-in user, their schools, and quick counts for
// the selected school. Counts come from the real list endpoints (we fetch up
// to the max page size and report what was returned — clearly labelled to
// avoid implying exact totals beyond the page cap).

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { useSchool } from '../lib/school-context';
import type {
  EnrollmentResponse,
  GuardianResponse,
  StaffResponse,
  StudentResponse,
} from '../types';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

interface Counts {
  students: number | null;
  guardians: number | null;
  staff: number | null;
  enrollments: number | null;
}

const MAX_COUNT_FETCH = 200; // backend max limit per request

export default function DashboardPage() {
  const { user } = useAuth();
  const isTeacher = (user?.roles ?? []).some((role) => role.name === 'TEACHER');
  const { schools, loading: schoolsLoading, selectedSchool, selectSchool, error: schoolError } = useSchool();
  const [counts, setCounts] = useState<Counts>({
    students: null,
    guardians: null,
    staff: null,
    enrollments: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeSchoolIdRef = useRef<string | null>(selectedSchool?.id ?? null);
  const requestIdRef = useRef(0);
  activeSchoolIdRef.current = selectedSchool?.id ?? null;

  useEffect(() => {
    requestIdRef.current += 1;
    setCounts({ students: null, guardians: null, staff: null, enrollments: null });
    setError(null);
    setLoading(false);
  }, [selectedSchool?.id]);

  const loadCounts = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    if (!selectedSchool) {
      setCounts({ students: null, guardians: null, staff: null, enrollments: null });
      setLoading(false);
      return;
    }
    const requestSchoolId = selectedSchool.id;
    setLoading(true);
    setError(null);
    const query = { school_id: requestSchoolId, limit: MAX_COUNT_FETCH };
    const [students, guardians, staff, enrollments] = await Promise.allSettled([
      api.get<StudentResponse[]>('/api/v1/students', query),
      api.get<GuardianResponse[]>('/api/v1/guardians', query),
      api.get<StaffResponse[]>('/api/v1/staff', query),
      api.get<EnrollmentResponse[]>('/api/v1/enrollments', query),
    ]);
    if (activeSchoolIdRef.current !== requestSchoolId || requestIdRef.current !== requestId) return;
    setCounts({
      students: students.status === 'fulfilled' ? students.value.length : null,
      guardians: guardians.status === 'fulfilled' ? guardians.value.length : null,
      staff: staff.status === 'fulfilled' ? staff.value.length : null,
      enrollments: enrollments.status === 'fulfilled' ? enrollments.value.length : null,
    });
    if (
      students.status === 'rejected' &&
      students.reason instanceof ApiError &&
      students.reason.status === 403
    ) {
      setError('You do not have access to view records for this school.');
    }
    setLoading(false);
  }, [selectedSchool]);

  useEffect(() => {
    void loadCounts();
  }, [loadCounts]);

  const countCards = [
    { label: 'Students', value: counts.students, to: '/students' },
    { label: 'Guardians', value: counts.guardians, to: '/guardians' },
    { label: 'Staff', value: counts.staff, to: '/staff' },
    { label: 'Enrollments', value: counts.enrollments, to: '/enrollments' },
  ].filter((card) => !isTeacher || ['Students', 'Enrollments'].includes(card.label));

  return (
    <div>
      <PageHeader
        title={`Welcome, ${user?.first_name ?? ''}`}
        subtitle={
          selectedSchool
            ? `Viewing data for ${selectedSchool.name}`
            : 'Choose a school below to open its dashboard and records.'
        }
        actions={selectedSchool ? <Button variant="secondary" onClick={() => selectSchool('')}>← Back to school selection</Button> : undefined}
      />

      {schoolError && <ErrorBanner message={schoolError} />}
      {error && <ErrorBanner message={error} />}

      {/* School-scoped counts */}
      {selectedSchool ? (
        loading ? (
          <Spinner />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {countCards.map((c) => (
              <Link key={c.label} to={c.to}>
                <Card className="p-5 transition-shadow hover:shadow-md">
                  <p className="text-sm font-medium text-slate-500">{c.label}</p>
                  <p className="mt-2 text-3xl font-semibold text-slate-900">
                    {c.value === null ? '—' : c.value}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    {c.value === MAX_COUNT_FETCH
                      ? `${MAX_COUNT_FETCH}+ records (page cap reached)`
                      : 'from live school data'}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        )
      ) : (
        <section aria-labelledby="school-selection-heading" className="mt-2">
          <div className="mb-4">
            <h2 id="school-selection-heading" className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Select a school
            </h2>
            <p className="mt-1 text-sm text-slate-500">Choose a school card to open its dashboard. You can return here at any time.</p>
          </div>
          {schoolsLoading ? (
            <Spinner label="Loading your schools…" />
          ) : schools.length === 0 ? (
            <Card className="p-6">
              <p className="text-sm text-slate-600">
                No schools are available to your account yet. Ask a platform administrator to assign you to a school.
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {schools.map((school) => (
                <button
                  key={school.id}
                  type="button"
                  disabled={!school.is_active}
                  onClick={() => selectSchool(school.id)}
                  aria-label={`Open ${school.name} dashboard`}
                  className="group w-full rounded-lg text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed"
                >
                  <Card className="h-full p-5 transition-all group-hover:-translate-y-0.5 group-hover:shadow-md group-focus-visible:ring-2 group-focus-visible:ring-indigo-600 disabled:opacity-60">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-900">{school.name}</p>
                        <p className="mt-1 text-sm text-slate-500">School code: {school.code}</p>
                        {school.city && <p className="mt-1 text-sm text-slate-500">{school.city}</p>}
                      </div>
                      <span className={school.is_active ? "rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700" : "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500"}>
                        {school.is_active ? 'Open school →' : 'Inactive'}
                      </span>
                    </div>
                  </Card>
                </button>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
