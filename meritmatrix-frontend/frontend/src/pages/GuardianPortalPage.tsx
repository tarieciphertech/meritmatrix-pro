import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

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
    <div>
      <PageHeader
        title="Guardian Portal"
        subtitle="View the students linked to your guardian account."
      />

      {error && <ErrorBanner message={error} />}

      {loading ? (
        <Spinner label="Loading linked students…" />
      ) : students.length === 0 ? (
        <Card className="p-6">
          <h2 className="font-semibold text-slate-900">No linked students yet</h2>
          <p className="mt-2 text-sm text-slate-600">
            This account does not currently match an active guardian record with linked students.
            Ask the school office to check that your guardian record has the same email address
            as your sign-in account and that your student relationship has been assigned.
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
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {students.map((student) => (
            <Card key={student.student_id} className="p-5">
              <div className="flex items-start justify-between gap-3">
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
              <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
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
              <p className="mt-4 text-xs text-slate-500">
                Academic results, attendance, and reports will appear here as those modules become
                available to guardian accounts.
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
