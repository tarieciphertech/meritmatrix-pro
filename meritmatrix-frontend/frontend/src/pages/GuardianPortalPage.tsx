import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

interface SubjectSummary {
  name: string;
  code: string;
}

interface CurrentEnrollment {
  class_name: string;
  class_code: string;
  academic_year: string;
  academic_year_is_current: boolean;
  enrollment_date?: string | null;
}

interface LinkedStudent {
  student_id: string;
  student_number: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  status: string;
  school_id: string;
  guardian_name: string;
  relationship_type: string;
  is_primary: boolean;
  receives_notifications: boolean;
  current_enrollment?: CurrentEnrollment | null;
  subjects: SubjectSummary[];
}

function titleCase(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function GuardianPortalPage() {
  const [students, setStudents] = useState<LinkedStudent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStudents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const linked = await api.get<LinkedStudent[]>('/api/v1/guardian-portal/students');
      setStudents(linked);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Unable to load your linked students. Please try again.',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStudents();
  }, [loadStudents]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Guardian Portal"
        subtitle="Your linked students, current class placement, and available school information."
      />

      {error && <ErrorBanner message={error} />}

      {loading ? (
        <Spinner label="Loading linked students…" />
      ) : students.length === 0 ? (
        <Card className="p-6">
          <h2 className="font-semibold text-slate-900">No linked students yet</h2>
          <p className="mt-2 text-sm text-slate-600">
            This account does not currently match an active guardian record with linked students.
            Ask the school office to check your guardian account and student relationship.
          </p>
          <button
            type="button"
            onClick={() => void loadStudents()}
            className="mt-4 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Check again
          </button>
        </Card>
      ) : (
        <div className="space-y-5">
          {students.map((student) => (
            <Card key={student.student_id} className="overflow-hidden">
              <div className="border-b border-slate-100 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900">
                      {student.first_name} {student.middle_name ? `${student.middle_name} ` : ''}
                      {student.last_name}
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Student number: {student.student_number}
                    </p>
                  </div>
                  <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
                    {titleCase(student.status)}
                  </span>
                </div>
                <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Relationship
                    </dt>
                    <dd className="mt-1 text-sm text-slate-800">
                      {titleCase(student.relationship_type)}
                      {student.is_primary ? ' · Primary contact' : ''}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Notifications
                    </dt>
                    <dd className="mt-1 text-sm text-slate-800">
                      {student.receives_notifications ? 'Enabled' : 'Not enabled'}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="grid grid-cols-1 gap-5 p-5 md:grid-cols-2">
                <section>
                  <h3 className="text-sm font-semibold text-slate-900">Current class placement</h3>
                  {student.current_enrollment ? (
                    <div className="mt-2 rounded-lg bg-slate-50 p-4">
                      <p className="font-medium text-slate-900">
                        {student.current_enrollment.class_name}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        Academic year: {student.current_enrollment.academic_year}
                      </p>
                      <p className="text-sm text-slate-600">
                        Class code: {student.current_enrollment.class_code}
                      </p>
                      {student.current_enrollment.enrollment_date && (
                        <p className="mt-1 text-xs text-slate-500">
                          Enrolled: {student.current_enrollment.enrollment_date}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="mt-2 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">
                      No active class enrollment is recorded for this student yet.
                    </p>
                  )}
                </section>

                <section>
                  <h3 className="text-sm font-semibold text-slate-900">Subjects</h3>
                  {student.subjects.length > 0 ? (
                    <ul className="mt-2 flex flex-wrap gap-2">
                      {student.subjects.map((subject) => (
                        <li
                          key={subject.code}
                          className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700"
                          title={subject.code}
                        >
                          {subject.name}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">
                      No subjects have been assigned to the current class yet.
                    </p>
                  )}
                </section>
              </div>

              <div className="border-t border-slate-100 bg-slate-50/70 p-5">
                <h3 className="text-sm font-semibold text-slate-900">Academic records</h3>
                <p className="mt-1 text-sm text-slate-600">
                  Results and grades, attendance history, downloadable reports, and fee balances
                  are not exposed by the current system yet. This portal will show verified records
                  here once those modules and their guardian-safe endpoints are implemented.
                </p>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
