// Enrollments management: list, create, and manage enrollment lifecycle
// (complete, withdraw, cancel) for the selected school.
// Uses GET/POST /api/v1/enrollments?school_id=..., PATCH /api/v1/enrollments/{id},
// POST /api/v1/enrollments/{id}/complete|withdraw|cancel.
// Also fetches students, academic years, and classes for dropdowns.

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type {
  AcademicYearResponse,
  ClassResponse,
  EnrollmentCreate,
  EnrollmentResponse,
  EnrollmentStatus,
  EnrollmentUpdate,
  StudentResponse,
} from '../types';
import { ENROLLMENT_STATUSES } from '../types';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Textarea,
} from '../components/ui';

const statusTone: Record<EnrollmentStatus, 'green' | 'slate' | 'amber' | 'red' | 'indigo'> = {
  active: 'green',
  completed: 'indigo',
  withdrawn: 'amber',
  transferred: 'amber',
  cancelled: 'red',
};

interface EnrollmentForm {
  student_id: string;
  academic_year_id: string;
  class_id: string;
  enrollment_date: string;
  withdrawal_date: string;
  status: EnrollmentStatus;
  enrollment_number: string;
  notes: string;
}

const emptyForm: EnrollmentForm = {
  student_id: '',
  academic_year_id: '',
  class_id: '',
  enrollment_date: '',
  withdrawal_date: '',
  status: 'active',
  enrollment_number: '',
  notes: '',
};

export default function EnrollmentsPage() {
  const { selectedSchool } = useSchool();
  const [enrollments, setEnrollments] = useState<EnrollmentResponse[]>([]);
  const [students, setStudents] = useState<StudentResponse[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYearResponse[]>([]);
  const [classes, setClasses] = useState<ClassResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingEnrollment, setEditingEnrollment] = useState<EnrollmentResponse | null>(null);
  const [form, setForm] = useState<EnrollmentForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const activeSchoolIdRef = useRef<string | null>(selectedSchool?.id ?? null);
  const loadRequestIdRef = useRef(0);

  const load = useCallback(async () => {
    if (!selectedSchool) {
      setEnrollments([]); setStudents([]); setAcademicYears([]); setClasses([]);
      setLoading(false);
      return;
    }
    const requestSchoolId = selectedSchool.id;
    const requestId = ++loadRequestIdRef.current;
    setEnrollments([]); setStudents([]); setAcademicYears([]); setClasses([]);
    setLoading(true);
    setError(null);
    try {
      const [enrollmentsList, studentsList, yearsList, classesList] = await Promise.all([
        api.get<EnrollmentResponse[]>('/api/v1/enrollments', {
          school_id: requestSchoolId,
          limit: 200,
        }),
        api.get<StudentResponse[]>('/api/v1/students', {
          school_id: requestSchoolId,
          limit: 200,
        }),
        api.get<AcademicYearResponse[]>('/api/v1/academic-years', {
          school_id: requestSchoolId,
        }),
        api.get<ClassResponse[]>('/api/v1/classes', {
          school_id: requestSchoolId,
        }),
      ]);
      if (activeSchoolIdRef.current !== requestSchoolId || loadRequestIdRef.current !== requestId) return;
      setEnrollments(enrollmentsList);
      setStudents(studentsList);
      setAcademicYears(yearsList);
      setClasses(classesList);
    } catch (err) {
      if (activeSchoolIdRef.current === requestSchoolId && loadRequestIdRef.current === requestId) {
        setEnrollments([]); setStudents([]); setAcademicYears([]); setClasses([]);
        setError(err instanceof Error ? err.message : 'Failed to load enrollments');
      }
    } finally {
      if (activeSchoolIdRef.current === requestSchoolId && loadRequestIdRef.current === requestId) setLoading(false);
    }
  }, [selectedSchool]);

  useEffect(() => {
    activeSchoolIdRef.current = selectedSchool?.id ?? null;
    loadRequestIdRef.current += 1;
    setEnrollments([]); setStudents([]); setAcademicYears([]); setClasses([]);
    setError(null);
    setModalOpen(false);
    setEditingEnrollment(null);
    setForm(emptyForm);
    setFormError(null);
  }, [selectedSchool?.id]);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditingEnrollment(null);
    setForm(emptyForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(enrollment: EnrollmentResponse) {
    setEditingEnrollment(enrollment);
    setForm({
      student_id: enrollment.student_id,
      academic_year_id: enrollment.academic_year_id,
      class_id: enrollment.class_id,
      enrollment_date: enrollment.enrollment_date ?? '',
      withdrawal_date: enrollment.withdrawal_date ?? '',
      status: enrollment.status,
      enrollment_number: enrollment.enrollment_number ?? '',
      notes: enrollment.notes ?? '',
    });
    setFormError(null);
    setModalOpen(true);
  }

  function setField(key: keyof EnrollmentForm, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!selectedSchool) return;
    setSaving(true);
    setFormError(null);
    try {
      if (editingEnrollment) {
        // Backend PATCH only accepts withdrawal_date, status, and notes.
        // Student, academic year, class, enrollment date, and enrollment
        // number are immutable by design.
        const payload: EnrollmentUpdate = {
          withdrawal_date: form.withdrawal_date || null,
          status: form.status,
          notes: form.notes || null,
        };
        await api.patch<EnrollmentResponse>(
          `/api/v1/enrollments/${editingEnrollment.id}`,
          payload,
        );
      } else {
        const payload: EnrollmentCreate = {
          student_id: form.student_id,
          academic_year_id: form.academic_year_id,
          class_id: form.class_id,
          enrollment_date: form.enrollment_date || null,
          status: form.status,
          enrollment_number: form.enrollment_number || null,
          notes: form.notes || null,
        };
        await api.post<EnrollmentResponse>('/api/v1/enrollments', payload);
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Failed to save enrollment');
    } finally {
      setSaving(false);
    }
  }

  async function handleAction(enrollment: EnrollmentResponse, action: 'complete' | 'withdraw' | 'cancel') {
    const labels: Record<string, string> = {
      complete: 'Mark as completed',
      withdraw: 'Withdraw',
      cancel: 'Cancel',
    };
    if (!window.confirm(`${labels[action]} this enrollment?`)) return;
    try {
      await api.post<EnrollmentResponse>(`/api/v1/enrollments/${enrollment.id}/${action}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} enrollment`);
    }
  }

  function studentName(id: string): string {
    const s = students.find((st) => st.id === id);
    return s ? `${s.first_name} ${s.last_name}` : id;
  }

  function yearName(id: string): string {
    const y = academicYears.find((ay) => ay.id === id);
    return y ? y.name : id;
  }

  function className(id: string): string {
    const c = classes.find((cl) => cl.id === id);
    return c ? c.name : id;
  }

  if (!selectedSchool) {
    return (
      <div>
        <PageHeader title="Enrollments" />
        <Card className="p-6">
          <p className="text-sm text-slate-600">
            Select a school from the header to view and manage enrollments.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Enrollments"
        subtitle={`Managing enrollments for ${selectedSchool.name}`}
        actions={<Button onClick={openCreate}>+ New Enrollment</Button>}
      />

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <Spinner />
      ) : enrollments.length === 0 ? (
        <Card>
          <EmptyState title="No enrollments found" hint="Create an enrollment to get started." />
        </Card>
      ) : (
        <Card>
          <Table headers={['Student', 'Academic Year', 'Class', 'Status', 'Enrollment Date', 'Actions']}>
            {enrollments.map((e) => (
              <tr key={e.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-900">{studentName(e.student_id)}</Td>
                <Td>{yearName(e.academic_year_id)}</Td>
                <Td>{className(e.class_id)}</Td>
                <Td>
                  <Badge tone={statusTone[e.status] ?? 'slate'}>{e.status}</Badge>
                </Td>
                <Td>{e.enrollment_date ?? '—'}</Td>
                <Td>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => openEdit(e)}>
                      Edit
                    </Button>
                    {e.status === 'active' && (
                      <>
                        <Button
                          variant="ghost"
                          className="!px-2 !py-1 text-xs"
                          onClick={() => handleAction(e, 'complete')}
                        >
                          Complete
                        </Button>
                        <Button
                          variant="ghost"
                          className="!px-2 !py-1 text-xs"
                          onClick={() => handleAction(e, 'withdraw')}
                        >
                          Withdraw
                        </Button>
                        <Button
                          variant="danger"
                          className="!px-2 !py-1 text-xs"
                          onClick={() => handleAction(e, 'cancel')}
                        >
                          Cancel
                        </Button>
                      </>
                    )}
                  </div>
                </Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      <Modal
        open={modalOpen}
        title={editingEnrollment ? 'Edit Enrollment' : 'New Enrollment'}
        onClose={() => setModalOpen(false)}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
              {formError}
            </div>
          )}

          <Field label="Student" required>
            <Select
              required
              disabled={!!editingEnrollment}
              value={form.student_id}
              onChange={(e) => setField('student_id', e.target.value)}
            >
              <option value="">Select a student…</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.first_name} {s.last_name} ({s.student_number})
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Academic Year" required>
            <Select
              required
              disabled={!!editingEnrollment}
              value={form.academic_year_id}
              onChange={(e) => setField('academic_year_id', e.target.value)}
            >
              <option value="">Select an academic year…</option>
              {academicYears.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.name}{y.is_current ? ' (current)' : ''}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Class" required>
            <Select
              required
              disabled={!!editingEnrollment}
              value={form.class_id}
              onChange={(e) => setField('class_id', e.target.value)}
            >
              <option value="">Select a class…</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.code})
                </option>
              ))}
            </Select>
          </Field>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Enrollment Date">
              <Input
                type="date"
                disabled={!!editingEnrollment}
                value={form.enrollment_date}
                onChange={(e) => setField('enrollment_date', e.target.value)}
              />
            </Field>
            <Field label="Status">
              <Select
                value={form.status}
                onChange={(e) => setField('status', e.target.value)}
              >
                {ENROLLMENT_STATUSES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </Select>
            </Field>
          </div>

          {editingEnrollment && (
            <Field label="Withdrawal Date">
              <Input
                type="date"
                value={form.withdrawal_date}
                onChange={(e) => setField('withdrawal_date', e.target.value)}
              />
            </Field>
          )}

          <Field label="Enrollment Number">
            <Input
              disabled={!!editingEnrollment}
              value={form.enrollment_number}
              onChange={(e) => setField('enrollment_number', e.target.value)}
            />
          </Field>

          <Field label="Notes">
            <Textarea
              rows={3}
              value={form.notes}
              onChange={(e) => setField('notes', e.target.value)}
            />
          </Field>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : editingEnrollment ? 'Save Changes' : 'Create Enrollment'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}