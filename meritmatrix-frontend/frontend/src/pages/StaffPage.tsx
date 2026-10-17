// Staff management: list, create, edit, and archive staff members for the
// selected school. Requires a selected school (school_id query param).
// Uses GET/POST /api/v1/staff?school_id=..., PATCH/DELETE /api/v1/staff/{id}.

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { EmploymentStatus, StaffAccountResponse, StaffCreate, StaffResponse, StaffUpdate } from '../types';
import { EMPLOYMENT_STATUSES } from '../types';
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

// Form model: create fields plus edit-only lifecycle fields
// (employment_status / termination_date are only accepted on PATCH).
interface StaffForm extends StaffCreate {
  employment_status: EmploymentStatus;
  termination_date: string;
}

const emptyForm: StaffForm = {
  staff_number: '',
  first_name: '',
  middle_name: '',
  last_name: '',
  email: '',
  phone: '',
  job_title: '',
  hire_date: '',
  notes: '',
  employment_status: 'active',
  termination_date: '',
};

const statusTone: Record<EmploymentStatus, 'green' | 'slate' | 'amber' | 'red' | 'indigo'> = {
  active: 'green',
  on_leave: 'amber',
  terminated: 'red',
  retired: 'slate',
  contract_ended: 'slate',
};

export default function StaffPage() {
  const { selectedSchool } = useSchool();
  const [staffList, setStaffList] = useState<StaffResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState<StaffResponse | null>(null);
  const [form, setForm] = useState<StaffForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedSchool) {
      setStaffList([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await api.get<StaffResponse[]>('/api/v1/staff', {
        school_id: selectedSchool.id,
        limit: 200,
      });
      setStaffList(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load staff');
    } finally {
      setLoading(false);
    }
  }, [selectedSchool]);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditingStaff(null);
    setForm(emptyForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(staff: StaffResponse) {
    setEditingStaff(staff);
    setForm({
      staff_number: staff.staff_number,
      first_name: staff.first_name,
      middle_name: staff.middle_name ?? '',
      last_name: staff.last_name,
      email: staff.email ?? '',
      phone: staff.phone ?? '',
      job_title: staff.job_title ?? '',
      hire_date: staff.hire_date ?? '',
      notes: staff.notes ?? '',
      employment_status: staff.employment_status,
      termination_date: staff.termination_date ?? '',
    });
    setFormError(null);
    setModalOpen(true);
  }

  function setField(key: keyof StaffForm, value: string) {
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
      payload.staff_number = form.staff_number;
      payload.first_name = form.first_name;
      payload.last_name = form.last_name;

      if (editingStaff) {
        const { staff_number: _sn, ...rest } = payload;
        const updatePayload: StaffUpdate = {
          ...(rest as StaffUpdate),
          employment_status: form.employment_status,
          termination_date: form.termination_date || null,
        };
        await api.patch<StaffResponse>(
          `/api/v1/staff/${editingStaff.id}`,
          updatePayload,
        );
      } else {
        // Create: backend defaults employment_status to active; the
        // termination_date field is not part of StaffCreate.
        const { employment_status: _es, termination_date: _td, ...createPayload } = payload;
        await api.post<StaffResponse>(
          '/api/v1/staff',
          createPayload,
          { school_id: selectedSchool.id },
        );
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Failed to save staff member');
    } finally {
      setSaving(false);
    }
  }

  async function handleEnableLogin(staff: StaffResponse) {
    if (!staff.email) {
      setError('Add an email address to this staff member before enabling login.');
      return;
    }
    const password = window.prompt(
      `Set an initial password for ${staff.first_name} ${staff.last_name}. Share it privately with the staff member.`,
    );
    if (password === null) return;
    if (password.length < 8 || password.length > 128 || !/[A-Za-z]/.test(password) || !/[0-9!@#$%^&*(),.?":{}|<>_+-]/.test(password)) {
      setError('Use a password of 8–128 characters containing letters and at least one number or symbol.');
      return;
    }
    setError(null);
    try {
      const account = await api.post<StaffAccountResponse>(
        `/api/v1/staff/${staff.id}/account`,
        { password },
      );
      window.alert(`Login enabled for ${account.email}. Role: ${account.role}. Give the initial password to the staff member privately.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enable staff login');
    }
  }

  async function handleArchive(staff: StaffResponse) {
    if (!window.confirm(`Archive "${staff.first_name} ${staff.last_name}"?`)) return;
    try {
      await api.delete<void>(`/api/v1/staff/${staff.id}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive staff member');
    }
  }

  if (!selectedSchool) {
    return (
      <div>
        <PageHeader title="Staff" />
        <Card className="p-6">
          <p className="text-sm text-slate-600">
            Select a school from the header to view and manage staff.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Staff"
        subtitle={`Managing staff for ${selectedSchool.name}`}
        actions={<Button onClick={openCreate}>+ New Staff Member</Button>}
      />

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <Spinner />
      ) : staffList.length === 0 ? (
        <Card>
          <EmptyState title="No staff found" hint="Add your first staff member to get started." />
        </Card>
      ) : (
        <Card>
          <Table headers={['Staff #', 'Name', 'Job Title', 'Status', 'Hire Date', 'Actions']}>
            {staffList.map((s) => (
              <tr key={s.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-900">{s.staff_number}</Td>
                <Td>
                  {s.first_name} {s.middle_name ? `${s.middle_name} ` : ''}{s.last_name}
                </Td>
                <Td>{s.job_title ?? '—'}</Td>
                <Td>
                  <Badge tone={statusTone[s.employment_status] ?? 'slate'}>
                    {s.employment_status}
                  </Badge>
                </Td>
                <Td>{s.hire_date ?? '—'}</Td>
                <Td>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => openEdit(s)}>
                      Edit
                    </Button>
                    {s.user_id ? (
                      <Badge tone="green">Login enabled</Badge>
                    ) : (
                      <Button
                        variant="ghost"
                        className="!px-2 !py-1 text-xs"
                        disabled={!s.email || !s.is_active || s.employment_status !== 'active'}
                        onClick={() => void handleEnableLogin(s)}
                      >
                        Enable login
                      </Button>
                    )}
                    <Button
                      variant="danger"
                      className="!px-2 !py-1 text-xs"
                      onClick={() => handleArchive(s)}
                    >
                      Archive
                    </Button>
                  </div>
                </Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      <Modal
        open={modalOpen}
        title={editingStaff ? 'Edit Staff Member' : 'New Staff Member'}
        onClose={() => setModalOpen(false)}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Staff Number" required>
              <Input
                required
                value={form.staff_number}
                onChange={(e) => setField('staff_number', e.target.value)}
                disabled={!!editingStaff}
              />
            </Field>
            <Field label="Job Title">
              <Input
                value={form.job_title ?? ''}
                onChange={(e) => setField('job_title', e.target.value)}
              />
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

          <Field label="Hire Date">
            <Input
              type="date"
              value={form.hire_date ?? ''}
              onChange={(e) => setField('hire_date', e.target.value)}
            />
          </Field>

          {editingStaff && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Employment Status">
                <Select
                  value={form.employment_status}
                  onChange={(e) => setField('employment_status', e.target.value)}
                >
                  {EMPLOYMENT_STATUSES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Termination Date">
                <Input
                  type="date"
                  value={form.termination_date}
                  onChange={(e) => setField('termination_date', e.target.value)}
                />
              </Field>
            </div>
          )}

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
              {saving ? 'Saving…' : editingStaff ? 'Save Changes' : 'Create Staff Member'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}