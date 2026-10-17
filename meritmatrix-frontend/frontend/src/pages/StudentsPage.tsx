// Students management: list, create, edit, and archive students for the
// selected school. Requires a selected school (school_id query param).
// Uses GET/POST /api/v1/students?school_id=..., PATCH/DELETE /api/v1/students/{id}.

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import { useAuth } from '../lib/auth';
import type { StudentCreate, StudentResponse, StudentStatus, StudentUpdate } from '../types';
import { STUDENT_STATUSES } from '../types';
import StudentGuardiansModal from './StudentGuardiansModal';
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

const emptyForm: StudentCreate = {
  student_number: '',
  first_name: '',
  middle_name: '',
  last_name: '',
  preferred_name: '',
  date_of_birth: '',
  gender: '',
  nationality: '',
  admission_date: '',
  status: 'active',
  email: '',
  phone: '',
  address: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  notes: '',
};

const statusTone: Record<StudentStatus, 'green' | 'slate' | 'amber' | 'red' | 'indigo'> = {
  active: 'green',
  inactive: 'slate',
  graduated: 'indigo',
  withdrawn: 'amber',
  transferred: 'amber',
  suspended: 'red',
};

export default function StudentsPage() {
  const { selectedSchool } = useSchool();
  const { user } = useAuth();
  const isTeacher = (user?.roles ?? []).some((role) => role.name === 'TEACHER');
  const canManageStudents = !isTeacher && (user?.roles ?? []).some((role) => ['SUPER_ADMIN', 'SCHOOL_ADMIN'].includes(role.name));
  const [students, setStudents] = useState<StudentResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingStudent, setEditingStudent] = useState<StudentResponse | null>(null);
  const [form, setForm] = useState<StudentCreate>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [guardianStudent, setGuardianStudent] = useState<StudentResponse | null>(null);
  const [viewingStudent, setViewingStudent] = useState<StudentResponse | null>(null);

  const load = useCallback(async () => {
    if (!selectedSchool) {
      setStudents([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await api.get<StudentResponse[]>('/api/v1/students', {
        school_id: selectedSchool.id,
        limit: 200,
      });
      setStudents(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load students');
    } finally {
      setLoading(false);
    }
  }, [selectedSchool]);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditingStudent(null);
    setForm(emptyForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(student: StudentResponse) {
    setEditingStudent(student);
    setForm({
      student_number: student.student_number,
      first_name: student.first_name,
      middle_name: student.middle_name ?? '',
      last_name: student.last_name,
      preferred_name: student.preferred_name ?? '',
      date_of_birth: student.date_of_birth ?? '',
      gender: student.gender ?? '',
      nationality: student.nationality ?? '',
      admission_date: student.admission_date ?? '',
      status: student.status,
      email: student.email ?? '',
      phone: student.phone ?? '',
      address: student.address ?? '',
      emergency_contact_name: student.emergency_contact_name ?? '',
      emergency_contact_phone: student.emergency_contact_phone ?? '',
      notes: student.notes ?? '',
    });
    setFormError(null);
    setModalOpen(true);
  }

  function setField(key: keyof StudentCreate, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!selectedSchool) return;
    setSaving(true);
    setFormError(null);
    try {
      const payload: Record<string, string | null> = {};
      for (const [key, value] of Object.entries(form)) {
        payload[key] = value === '' ? null : value;
      }
      payload.student_number = form.student_number;
      payload.first_name = form.first_name;
      payload.last_name = form.last_name;
      payload.status = form.status ?? 'active';

      let newlyCreatedStudent: StudentResponse | null = null;
      if (editingStudent) {
        const { student_number: _sn, ...rest } = payload;
        await api.patch<StudentResponse>(
          `/api/v1/students/${editingStudent.id}`,
          rest as StudentUpdate,
        );
      } else {
        newlyCreatedStudent = await api.post<StudentResponse>(
          '/api/v1/students',
          payload,
          { school_id: selectedSchool.id },
        );
      }
      setModalOpen(false);
      await load();
      if (newlyCreatedStudent) setGuardianStudent(newlyCreatedStudent);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Failed to save student');
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive(student: StudentResponse) {
    if (!window.confirm(`Archive "${student.first_name} ${student.last_name}"?`)) return;
    try {
      await api.delete<void>(`/api/v1/students/${student.id}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive student');
    }
  }

  if (!selectedSchool) {
    return (
      <div>
        <PageHeader title="Students" />
        <Card className="p-6">
          <p className="text-sm text-slate-600">
            Select a school from the header to view and manage students.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Students"
        subtitle={`${isTeacher ? 'Viewing students assigned to you at' : 'Managing students for'} ${selectedSchool.name}`}
        actions={canManageStudents ? <Button onClick={openCreate}>+ New Student</Button> : undefined}
      />

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <Spinner />
      ) : students.length === 0 ? (
        <Card>
          <EmptyState title="No students found" hint="Add your first student to get started." />
        </Card>
      ) : (
        <Card>
          <Table headers={['Student #', 'Name', 'Gender', 'Status', 'Admission Date', canManageStudents ? 'Actions' : 'Details']}>
            {students.map((s) => (
              <tr key={s.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-900">{s.student_number}</Td>
                <Td>
                  {s.first_name} {s.middle_name ? `${s.middle_name} ` : ''}{s.last_name}
                </Td>
                <Td>{s.gender ?? '—'}</Td>
                <Td>
                  <Badge tone={statusTone[s.status] ?? 'slate'}>{s.status}</Badge>
                </Td>
                <Td>{s.admission_date ?? '—'}</Td>
                <Td>
                  {canManageStudents ? (
                    <div className="flex items-center gap-2">
                      <Button variant="secondary" className="!px-2 !py-1 text-xs" onClick={() => setGuardianStudent(s)}>
                        Guardians
                      </Button>
                      <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => openEdit(s)}>
                        Edit
                      </Button>
                      <Button
                        variant="danger"
                        className="!px-2 !py-1 text-xs"
                        onClick={() => handleArchive(s)}
                      >
                        Archive
                      </Button>
                    </div>
                  ) : (
                    <Button variant="secondary" className="!px-2 !py-1 text-xs" onClick={() => setViewingStudent(s)}>
                      View details
                    </Button>
                  )}
                </Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      <Modal
        open={modalOpen}
        title={editingStudent ? 'Edit Student' : 'New Student'}
        onClose={() => setModalOpen(false)}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Student Number" required>
              <Input
                required
                value={form.student_number}
                onChange={(e) => setField('student_number', e.target.value)}
                disabled={!!editingStudent}
              />
            </Field>
            <Field label="Status">
              <Select
                value={form.status ?? 'active'}
                onChange={(e) => setField('status', e.target.value)}
              >
                {STUDENT_STATUSES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="First Name" required>
              <Input
                required
                value={form.first_name}
                onChange={(e) => setField('first_name', e.target.value)}
              />
            </Field>
            <Field label="Middle Name">
              <Input
                value={form.middle_name ?? ''}
                onChange={(e) => setField('middle_name', e.target.value)}
              />
            </Field>
            <Field label="Last Name" required>
              <Input
                required
                value={form.last_name}
                onChange={(e) => setField('last_name', e.target.value)}
              />
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Preferred Name">
              <Input
                value={form.preferred_name ?? ''}
                onChange={(e) => setField('preferred_name', e.target.value)}
              />
            </Field>
            <Field label="Gender">
              <Select
                value={form.gender ?? ''}
                onChange={(e) => setField('gender', e.target.value)}
              >
                <option value="">Select…</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </Select>
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Date of Birth">
              <Input
                type="date"
                value={form.date_of_birth ?? ''}
                onChange={(e) => setField('date_of_birth', e.target.value)}
              />
            </Field>
            <Field label="Admission Date">
              <Input
                type="date"
                value={form.admission_date ?? ''}
                onChange={(e) => setField('admission_date', e.target.value)}
              />
            </Field>
          </div>

          <Field label="Nationality">
            <Input
              value={form.nationality ?? ''}
              onChange={(e) => setField('nationality', e.target.value)}
            />
          </Field>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Email">
              <Input
                type="email"
                value={form.email ?? ''}
                onChange={(e) => setField('email', e.target.value)}
              />
            </Field>
            <Field label="Phone">
              <Input
                value={form.phone ?? ''}
                onChange={(e) => setField('phone', e.target.value)}
              />
            </Field>
          </div>

          <Field label="Address">
            <Input
              value={form.address ?? ''}
              onChange={(e) => setField('address', e.target.value)}
            />
          </Field>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Emergency Contact Name">
              <Input
                value={form.emergency_contact_name ?? ''}
                onChange={(e) => setField('emergency_contact_name', e.target.value)}
              />
            </Field>
            <Field label="Emergency Contact Phone">
              <Input
                value={form.emergency_contact_phone ?? ''}
                onChange={(e) => setField('emergency_contact_phone', e.target.value)}
              />
            </Field>
          </div>

          <Field label="Notes">
            <Textarea
              rows={3}
              value={form.notes ?? ''}
              onChange={(e) => setField('notes', e.target.value)}
            />
          </Field>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : editingStudent ? 'Save Changes' : 'Create Student'}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={!!viewingStudent}
        title="Student details"
        onClose={() => setViewingStudent(null)}
      >
        {viewingStudent && <div className="space-y-4 text-sm">
          <div className="rounded-md bg-slate-50 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Student</p>
            <p className="mt-1 text-lg font-semibold text-slate-900">{[viewingStudent.first_name, viewingStudent.middle_name, viewingStudent.last_name].filter(Boolean).join(' ')}</p>
            <p className="text-slate-600">{viewingStudent.student_number}</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><p className="text-slate-500">Preferred name</p><p className="font-medium">{viewingStudent.preferred_name || '—'}</p></div>
            <div><p className="text-slate-500">Status</p><p className="font-medium">{viewingStudent.status}</p></div>
            <div><p className="text-slate-500">Date of birth</p><p className="font-medium">{viewingStudent.date_of_birth || '—'}</p></div>
            <div><p className="text-slate-500">Gender</p><p className="font-medium">{viewingStudent.gender || '—'}</p></div>
            <div><p className="text-slate-500">Nationality</p><p className="font-medium">{viewingStudent.nationality || '—'}</p></div>
            <div><p className="text-slate-500">Admission date</p><p className="font-medium">{viewingStudent.admission_date || '—'}</p></div>
            <div><p className="text-slate-500">Email</p><p className="font-medium break-words">{viewingStudent.email || '—'}</p></div>
            <div><p className="text-slate-500">Phone</p><p className="font-medium">{viewingStudent.phone || '—'}</p></div>
            <div className="sm:col-span-2"><p className="text-slate-500">Address</p><p className="font-medium">{viewingStudent.address || '—'}</p></div>
            <div><p className="text-slate-500">Emergency contact</p><p className="font-medium">{viewingStudent.emergency_contact_name || '—'}</p></div>
            <div><p className="text-slate-500">Emergency contact phone</p><p className="font-medium">{viewingStudent.emergency_contact_phone || '—'}</p></div>
            <div className="sm:col-span-2"><p className="text-slate-500">Notes</p><p className="whitespace-pre-wrap font-medium">{viewingStudent.notes || '—'}</p></div>
          </div>
          <div className="flex justify-end"><Button variant="secondary" onClick={() => setViewingStudent(null)}>Close</Button></div>
        </div>}
      </Modal>

      <StudentGuardiansModal
        student={guardianStudent}
        schoolId={selectedSchool.id}
        onClose={() => setGuardianStudent(null)}
      />
    </div>
  );
}