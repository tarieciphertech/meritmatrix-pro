import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';
import GuardianNotificationInbox from '../components/GuardianNotificationInbox';

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
  academic_results?: { assessment_title: string; assessment_type: string; subject_name: string; term_name: string; score: number; max_score: number; percentage: number; grade_label?: string | null; weight_percent: number; remarks?: string | null; date?: string | null }[];
  fee_summary?: { currency?: string | null; charges_total: number; payments_total: number; balance: number; charges_count: number };
  fee_transactions?: { kind: string; date: string; description: string; amount: number; reference?: string | null }[];
  attendance?: {
    total_marked: number;
    present: number;
    absent: number;
    late: number;
    excused: number;
    sick: number;
    left_early: number;
    attendance_rate: number | null;
    recent_records: { date: string; session: string; status: string }[];
  };
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
  const loadRequestIdRef = useRef(0);

  const loadStudents = useCallback(async () => {
    const requestId = ++loadRequestIdRef.current;
    // Clear prior-school student information before loading a new selection.
    setStudents([]);
    setLoading(true);
    setError(null);
    try {
      const availableSchools = await api.get<PortalSchool[]>('/api/v1/guardian-portal/schools');
      if (loadRequestIdRef.current !== requestId) return;
      setSchools(availableSchools);
      const chosenId = availableSchools.some((school) => school.id === schoolId)
        ? schoolId
        : availableSchools.length === 1 ? availableSchools[0].id : '';
      setSchoolId(chosenId);
      const linked = chosenId
        ? await api.get<LinkedStudent[]>('/api/v1/guardian-portal/students', { school_id: chosenId })
        : [];
      if (loadRequestIdRef.current !== requestId) return;
      setStudents(linked);
    } catch (err) {
      if (loadRequestIdRef.current === requestId) {
        setStudents([]);
        setError(
          err instanceof ApiError
            ? err.message
            : 'Unable to load your linked students. Please try again.',
        );
      }
    } finally {
      if (loadRequestIdRef.current === requestId) setLoading(false);
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

      {schoolId && !loading && <div className="mb-5"><GuardianNotificationInbox schoolId={schoolId} /></div>}

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
            This account does not currently have an active guardian record with linked students.
            Ask the school office to confirm your guardian account is linked to the correct student.
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

              <div className="mt-5 border-t border-slate-100 pt-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">Attendance overview</h3>
                  <span className="text-sm font-medium text-slate-700">
                    {student.attendance?.attendance_rate == null
                      ? 'No attendance recorded'
                      : `${student.attendance.attendance_rate}% present`}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                  {[
                    ['Present', student.attendance?.present ?? 0],
                    ['Absent', student.attendance?.absent ?? 0],
                    ['Late', student.attendance?.late ?? 0],
                    ['Excused', student.attendance?.excused ?? 0],
                    ['Sick', student.attendance?.sick ?? 0],
                    ['Left early', student.attendance?.left_early ?? 0],
                  ].map(([label, count]) => (
                    <div key={label} className="rounded-lg bg-slate-50 p-3">
                      <p className="text-xs text-slate-500">{label}</p>
                      <p className="mt-1 text-lg font-semibold text-slate-900">{count}</p>
                    </div>
                  ))}
                </div>
                {student.attendance?.recent_records && student.attendance.recent_records.length > 0 ? (
                  <div className="mt-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recent attendance</h4>
                    <ul className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200">
                      {student.attendance.recent_records.map((record) => (
                        <li key={record.date + '-' + record.session} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                          <span className="text-slate-700">{record.date} · {titleCase(record.session)}</span>
                          <span className="font-medium text-slate-900">{titleCase(record.status)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-slate-500">No attendance entries have been saved for this student yet.</p>
                )}
              </div>

              <div className="mt-5 border-t border-slate-100 pt-4">
                <h3 className="text-sm font-semibold text-slate-900">Published academic results</h3>
                {student.academic_results && student.academic_results.length > 0 ? (
                  <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead className="bg-slate-50"><tr>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500">Subject / assessment</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500">Term</th>
                        <th className="px-3 py-2 text-right text-xs font-semibold text-slate-500">Result</th>
                      </tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {student.academic_results.map((result, index) => (
                          <tr key={result.assessment_title + result.subject_name + result.term_name + index}>
                            <td className="px-3 py-2">
                              <p className="font-medium text-slate-800">{result.subject_name}</p>
                              <p className="text-xs text-slate-500">{result.assessment_title} · {titleCase(result.assessment_type)}</p>
                            </td>
                            <td className="px-3 py-2 text-slate-600">{result.term_name}</td>
                            <td className="px-3 py-2 text-right">
                              <p className="font-semibold text-slate-900">{result.score} / {result.max_score}</p>
                              <p className="text-xs text-slate-500">{result.percentage}%{result.grade_label ? ' · Grade ' + result.grade_label : ''}</p>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">No published results are available yet. Results appear here after the school publishes assessments.</p>
                )}
              </div>
              <div className="mt-5 border-t border-slate-100 pt-4">
                <h3 className="text-sm font-semibold text-slate-900">Fees and payments</h3>
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {[
                    ['Charges', student.fee_summary?.charges_total ?? 0],
                    ['Paid', student.fee_summary?.payments_total ?? 0],
                    ['Balance', student.fee_summary?.balance ?? 0],
                  ].map(([label, amount]) => (
                    <div key={label} className="rounded-lg bg-slate-50 p-3">
                      <p className="text-xs text-slate-500">{label}</p>
                      <p className="mt-1 text-lg font-semibold text-slate-900">{student.fee_summary?.currency ? student.fee_summary.currency + ' ' : ''}{Number(amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
                    </div>
                  ))}
                </div>
                {student.fee_transactions && student.fee_transactions.length > 0 ? (
                  <ul className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200">
                    {student.fee_transactions.map((item, index) => (
                      <li key={item.kind + item.date + item.description + index} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                        <div><p className="font-medium text-slate-800">{item.description}</p><p className="text-xs text-slate-500">{item.date} · {titleCase(item.kind)}{item.reference ? ' · ' + item.reference : ''}</p></div>
                        <span className="whitespace-nowrap font-semibold text-slate-900">{item.kind === 'payment' ? '−' : ''}{student.fee_summary?.currency ? student.fee_summary.currency + ' ' : ''}{item.amount}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-slate-500">No fee charges or payments have been recorded for this student yet.</p>
                )}
              </div>            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
