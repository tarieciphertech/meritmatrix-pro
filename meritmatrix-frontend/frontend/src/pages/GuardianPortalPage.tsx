import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

interface PortalSchool { id: string; name: string; code: string; country?: string | null; country_code?: string | null; }

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
  current_enrollment?: {
    class_name: string;
    class_code?: string | null;
    academic_year: string;
    academic_year_is_current: boolean;
    enrollment_date?: string | null;
  } | null;
  subjects?: { name: string; code?: string | null }[];
}

function titleCase(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function GuardianPortalPage() {
  const [students, setStudents] = useState<LinkedStudent[]>([]);
  const [schools, setSchools] = useState<PortalSchool[]>([]);
  const [schoolId, setSchoolId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStudents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const availableSchools = await api.get<PortalSchool[]>('/api/v1/guardian-portal/schools');
      setSchools(availableSchools);
      const chosenId = availableSchools.some((school) => school.id === schoolId)
        ? schoolId
        : availableSchools.length === 1 ? availableSchools[0].id : '';
      setSchoolId(chosenId);
      const linked = chosenId
        ? await api.get<LinkedStudent[]>('/api/v1/guardian-portal/students', { school_id: chosenId })
        : [];
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
  }, [schoolId]);

  useEffect(() => {
    void loadStudents();
  }, [loadStudents]);

  return (
    <div>
      <PageHeader
        title="Guardian Portal"
        subtitle="Choose the school to view only students linked to your guardian account."
      />

      {!loading && schools.length > 0 && (
        <div className="mb-5 max-w-xl rounded-lg border border-slate-200 bg-white p-4">
          <label htmlFor="guardian-school" className="block text-sm font-medium text-slate-700">School</label>
          <select id="guardian-school" value={schoolId} onChange={(event) => setSchoolId(event.target.value)}
            className="mt-2 block w-full rounded-md border border-slate-300 bg-white p-2.5 text-sm">
            <option value="">Select your school…</option>
            {schools.map((school) => <option key={school.id} value={school.id}>{school.name} ({school.code})</option>)}
          </select>
          <p className="mt-2 text-xs text-slate-500">Only schools with your linked students are listed.</p>
        </div>
      )}

      {error && <ErrorBanner message={error} />}

      {!loading && schools.length === 0 ? (
        <Card className="p-6"><h2 className="font-semibold text-slate-900">No school access found</h2><p className="mt-2 text-sm text-slate-600">Ask the school office to confirm that your guardian account is linked to an active student.</p><button type="button" onClick={() => void loadStudents()} className="mt-4 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white">Check again</button></Card>
      ) : loading ? (
        <Spinner label="Loading linked students…" />
      ) : !schoolId ? (
        <Card className="p-6"><p className="text-sm text-slate-600">Select a school to continue to its guardian portal.</p></Card>
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
              <div className="mt-5 border-t border-slate-100 pt-4">
                <h3 className="text-sm font-semibold text-slate-900">Current class placement</h3>
                {student.current_enrollment ? (
                  <div className="mt-2 rounded-lg bg-slate-50 p-3">
                    <p className="font-medium text-slate-900">{student.current_enrollment.class_name}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      Academic year: {student.current_enrollment.academic_year}
                      {student.current_enrollment.academic_year_is_current ? ' · Current year' : ''}
                    </p>
                    {student.current_enrollment.class_code && (
                      <p className="mt-1 text-xs text-slate-500">Class code: {student.current_enrollment.class_code}</p>
                    )}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">No active class enrollment is recorded yet.</p>
                )}
              </div>

              <div className="mt-4">
                <h3 className="text-sm font-semibold text-slate-900">Assigned subjects</h3>
                {student.subjects && student.subjects.length > 0 ? (
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {student.subjects.map((subject) => (
                      <li key={(subject.code ?? '') + '-' + subject.name} className="rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-sm text-indigo-800">
                        {subject.name}{subject.code ? ' (' + subject.code + ')' : ''}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">No active subjects are linked to this class yet.</p>
                )}
              </div>

              <div className="mt-5 grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 sm:grid-cols-3">
                <div className="rounded-lg border border-slate-200 p-3">
                  <h3 className="text-sm font-semibold text-slate-900">Academic results</h3>
                  <p className="mt-1 text-xs text-slate-500">Results will appear when assessment records are available to guardians.</p>
                </div>
                <div className="rounded-lg border border-slate-200 p-3">
                  <h3 className="text-sm font-semibold text-slate-900">Attendance</h3>
                  <p className="mt-1 text-xs text-slate-500">Attendance records are not yet exposed in the guardian portal.</p>
                </div>
                <div className="rounded-lg border border-slate-200 p-3">
                  <h3 className="text-sm font-semibold text-slate-900">Fees and reports</h3>
                  <p className="mt-1 text-xs text-slate-500">Fee balances and report cards will appear once those records are available.</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
