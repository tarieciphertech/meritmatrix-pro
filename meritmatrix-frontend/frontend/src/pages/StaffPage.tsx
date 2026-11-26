// Staff management: list, create, edit, and archive staff members for the
// selected school. Requires a selected school (school_id query param).
// Uses GET/POST /api/v1/staff?school_id=..., PATCH/DELETE /api/v1/staff/{id}.

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
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
type SchoolPosition = { id: string; name: string; code: string; description?: string | null; permission_names: string[]; is_system: boolean; is_active: boolean };

interface StaffForm extends StaffCreate {
  employment_status: EmploymentStatus;
  termination_date: string;
}

const emptyForm: StaffForm = {
  staff_number: '',
  ec_number: '',
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
  const [positions, setPositions] = useState<SchoolPosition[]>([]);
  const [effectivePermissions, setEffectivePermissions] = useState<string[]>([]);
  const [positionModalOpen, setPositionModalOpen] = useState(false);
  const [positionStaff, setPositionStaff] = useState<StaffResponse | null>(null);
  const [selectedPositionIds, setSelectedPositionIds] = useState<string[]>([]);
  const [savingPositions, setSavingPositions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState<StaffResponse | null>(null);
  const [form, setForm] = useState<StaffForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const can = (permission: string) => effectivePermissions.includes('system.admin') || effectivePermissions.includes(permission);
  const activeSchoolIdRef = useRef<string | null>(selectedSchool?.id ?? null);
  const loadRequestIdRef = useRef(0);

  const load = useCallback(async () => {
    if (!selectedSchool) {
      setStaffList([]);
      setLoading(false);
      return;
    }
    const requestSchoolId = selectedSchool.id;
    const requestId = ++loadRequestIdRef.current;
    setStaffList([]);
    setLoading(true);
    setError(null);
    try {
      const [list, positionRows, permissionResult] = await Promise.all([
        api.get<StaffResponse[]>('/api/v1/staff', { school_id: requestSchoolId, limit: 200 }),
        api.get<SchoolPosition[]>('/api/v1/school-positions', { school_id: requestSchoolId }),
        api.get<{ position_codes: string[]; permission_names: string[] }>('/api/v1/school-positions/me', { school_id: requestSchoolId }),
      ]);
      if (activeSchoolIdRef.current !== requestSchoolId || loadRequestIdRef.current !== requestId) return;
      setStaffList(list);
      setPositions(positionRows);
      setEffectivePermissions(permissionResult.permission_names);
    } catch (err) {
      if (activeSchoolIdRef.current === requestSchoolId && loadRequestIdRef.current === requestId) {
        setStaffList([]);
        setError(err instanceof Error ? err.message : 'Failed to load staff');
      }
    } finally {
      if (activeSchoolIdRef.current === requestSchoolId && loadRequestIdRef.current === requestId) setLoading(false);
    }
  }, [selectedSchool]);

  useEffect(() => {
    activeSchoolIdRef.current = selectedSchool?.id ?? null;
    loadRequestIdRef.current += 1;
    setStaffList([]);
    setPositions([]);
    setEffectivePermissions([]);
    setPositionModalOpen(false);
    setPositionStaff(null);
    setSelectedPositionIds([]);
    setError(null);
    setModalOpen(false);
    setEditingStaff(null);
    setForm(emptyForm);
    setFormError(null);
  }, [selectedSchool?.id]);

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
      ec_number: staff.ec_number ?? '',
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


  async function openPositionManager(staff: StaffResponse) {
    if (!selectedSchool) return;
    setPositionStaff(staff);
    setSelectedPositionIds([]);
    try {
      const result = await api.get<{ staff_id: string; positions: SchoolPosition[] }>(
        '/api/v1/school-positions/staff/' + staff.id, { school_id: selectedSchool.id },
      );
      setSelectedPositionIds(result.positions.map(position => position.id));
      setPositionModalOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load staff positions');
    }
  }

  async function savePositions() {
    if (!selectedSchool || !positionStaff) return;
    setSavingPositions(true);
    setError(null);
    try {
      await api.put(
        '/api/v1/school-positions/staff/' + positionStaff.id,
        { position_ids: selectedPositionIds },
        { school_id: selectedSchool.id },
      );
      setPositionModalOpen(false);
      setPositionStaff(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save staff positions');
    } finally {
      setSavingPositions(false);
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
    if (password.length < 12 || password.length > 128 || !/[A-Za-z]/.test(password) || !/[0-9!@#$%^&*(),.?":{}|<>_+-]/.test(password)) {
      setError('Use a password of 12–128 characters containing letters and at least one number or symbol.');
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
        actions={can('staff.create') ? <Button onClick={openCreate}>+ New Staff Member</Button> : undefined}
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
          <Table headers={['Staff #', 'EC Number', 'Name', 'Job Title', 'Status', 'Hire Date', 'Actions']}>
            {staffList.map((s) => (
              <tr key={s.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-900">{s.staff_number}</Td>
                <Td>{s.ec_number ?? '—'}</Td>
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
                    {can('staff.update') && <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => openEdit(s)}>Edit</Button>}
                    {can('staff.update') && <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => void openPositionManager(s)}>Positions</Button>}
                    {can('staff.update') && (s.user_id ? (
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
                    ))}
                    {can('staff.delete') && <Button
                      variant="danger"
                      className="!px-2 !py-1 text-xs"
                      onClick={() => handleArchive(s)}
                    >
                      Archive
                    </Button>}
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
            <Field label="EC Number (optional)">
              <Input
                value={form.ec_number ?? ''}
                onChange={(e) => setField('ec_number', e.target.value)}
                placeholder="e.g. 123456A"
                autoComplete="off"
              />
              <p className="mt-1 text-xs text-slate-500">For Zimbabwean public-service teachers, enter the EC number as issued by the Public Service Commission. It is normalized to uppercase; leave blank when not applicable.</p>
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

      <Modal
        open={positionModalOpen}
        title={positionStaff ? 'School positions · ' + positionStaff.first_name + ' ' + positionStaff.last_name : 'School positions'}
        onClose={() => setPositionModalOpen(false)}
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Assign one or more positions. Their permissions are combined, and all access remains limited to this school.</p>
          <div className="max-h-80 space-y-2 overflow-y-auto rounded-md border border-slate-200 p-3">
            {positions.map(position => (
              <label key={position.id} className="flex cursor-pointer items-start gap-3 rounded-md p-2 hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={selectedPositionIds.includes(position.id)}
                  onChange={event => setSelectedPositionIds(current =>
                    event.target.checked
                      ? [...current, position.id]
                      : current.filter(id => id !== position.id)
                  )}
                  className="mt-1"
                />
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-slate-900">{position.name}</span>
                  <span className="block text-xs text-slate-500">{position.description || position.code}</span>
                </span>
              </label>
            ))}
          </div>
          <div className="flex justify-between gap-2">
            <span className="self-center text-xs text-slate-500">{selectedPositionIds.length} position(s) selected</span>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setPositionModalOpen(false)}>Cancel</Button>
              <Button onClick={() => void savePositions()} disabled={savingPositions}>{savingPositions ? 'Saving…' : 'Save positions'}</Button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}