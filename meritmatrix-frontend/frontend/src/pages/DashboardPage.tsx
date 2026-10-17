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
import { Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

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
  const { schools, selectedSchool, error: schoolError } = useSchool();
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
            : 'Select a school from the header to view its data.'
        }
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
        <Card className="p-6">
          <p className="text-sm text-slate-600">
            No school selected yet. Use the school selector in the header to browse students,
            guardians, staff, and enrollments.
          </p>
        </Card>
      )}

      {/* Your schools */}
      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Your schools ({schools.length})
        </h2>
        {schools.length === 0 ? (
          <Card className="p-6">
            <p className="text-sm text-slate-600">
              You are not a member of any school yet. Ask a platform administrator to assign you
              to a school.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {schools.map((s) => (
              <Card key={s.id} className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-slate-900">{s.name}</p>
                    <p className="mt-0.5 text-sm text-slate-500">Code: {s.code}</p>
                    {s.city && <p className="text-sm text-slate-500">{s.city}</p>}
                  </div>
                  {!s.is_active && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                      Inactive
                    </span>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
