// Schools management: list, create, edit, and deactivate schools.
// Uses GET /api/v1/schools, POST /api/v1/schools, PATCH /api/v1/schools/{id},
// DELETE /api/v1/schools/{id} (deactivate).

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { SchoolCreate, SchoolResponse, SchoolUpdate } from '../types';
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
  Spinner,
  Table,
  Td,
} from '../components/ui';

type SchoolAdminStatus = {
  school_id: string; school_name: string; configured: boolean; user_id: string;
  first_name: string; last_name: string; email: string; is_active: boolean; must_change_password: boolean;
};
type SchoolAdminForm = { first_name: string; last_name: string; email: string; password: string };
const emptyAdminForm: SchoolAdminForm = { first_name: '', last_name: '', email: '', password: '' };

const emptyForm: SchoolCreate = {
  name: '',
  code: '',
  registration_number: '',
  address: '',
  city: '',
  country: '',
  phone: '',
  email: '',
  website: '',
  timezone: '',
  currency: '',
};

export default function SchoolsPage() {
  const { hasRole } = useAuth();
  const [schools, setSchools] = useState<SchoolResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSchool, setEditingSchool] = useState<SchoolResponse | null>(null);
  const [form, setForm] = useState<SchoolCreate>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [adminAccounts, setAdminAccounts] = useState<SchoolAdminStatus[]>([]);
  const [creatingAdminFor, setCreatingAdminFor] = useState<SchoolResponse | null>(null);
  const [adminForm, setAdminForm] = useState<SchoolAdminForm>(emptyAdminForm);
  const [adminSaving, setAdminSaving] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [adminSuccess, setAdminSuccess] = useState<string | null>(null);

  const canManage = hasRole('SUPER_ADMIN');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.get<SchoolResponse[]>('/api/v1/schools', { limit: 200 });
      setSchools(list);
      if (canManage) setAdminAccounts(await api.get<SchoolAdminStatus[]>('/api/v1/schools/admin-accounts'));
      else setAdminAccounts([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schools');
    } finally {
      setLoading(false);
    }
  }, [canManage]);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditingSchool(null);
    setForm(emptyForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(school: SchoolResponse) {
    setEditingSchool(school);
    setForm({
      name: school.name,
      code: school.code,
      registration_number: school.registration_number ?? '',
      address: school.address ?? '',
      city: school.city ?? '',
      country: school.country ?? '',
      phone: school.phone ?? '',
      email: school.email ?? '',
      website: school.website ?? '',
      timezone: school.timezone ?? '',
      currency: school.currency ?? '',
    });
    setFormError(null);
    setModalOpen(true);
  }

  function setField(key: keyof SchoolCreate, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      // Strip empty optional strings to null so the backend treats them as absent.
      const payload: Record<string, string | null> = {};
      for (const [key, value] of Object.entries(form)) {
        payload[key] = value === '' ? null : value;
      }
      // Required fields must not be null.
      payload.name = form.name;
      payload.code = form.code;

      if (editingSchool) {
        const updatePayload: SchoolUpdate = { ...payload };
        await api.patch<SchoolResponse>(`/api/v1/schools/${editingSchool.id}`, updatePayload);
      } else {
        await api.post<SchoolResponse>('/api/v1/schools', payload);
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Failed to save school');
    } finally {
      setSaving(false);
    }
  }

  function openAdminSetup(school: SchoolResponse) {
    setCreatingAdminFor(school); setAdminForm(emptyAdminForm); setAdminError(null);
  }

  async function handleCreateAdmin(e: FormEvent) {
    e.preventDefault();
    if (!creatingAdminFor) return;
    if (adminForm.password.length < 12) { setAdminError('Use an initial password of at least 12 characters.'); return; }
    setAdminSaving(true); setAdminError(null);
    try {
      const created = await api.post<{ user_id: string; school_id: string; school_name: string; first_name: string; last_name: string; email: string; role: string; must_change_password: boolean }>(
        '/api/v1/schools/' + creatingAdminFor.id + '/admin-account', adminForm,
      );
      setAdminSuccess('Administrator account created for ' + created.school_name + ': ' + created.email + '. The administrator must change the initial password at first sign-in.');
      setCreatingAdminFor(null); setAdminForm(emptyAdminForm); await load();
    } catch (err) {
      setAdminError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Could not create the school administrator account.');
    } finally { setAdminSaving(false); }
  }

  async function handleDeactivate(school: SchoolResponse) {
    if (!window.confirm(`Deactivate "${school.name}"? This will mark it inactive.`)) return;
    try {
      await api.delete<void>(`/api/v1/schools/${school.id}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate school');
    }
  }

  return (
    <div>
      <PageHeader
        title="Schools"
        subtitle="Manage schools in the platform"
        actions={
          canManage ? (
            <Button onClick={openCreate}>+ New School</Button>
          ) : undefined
        }
      />

      {error && <ErrorBanner message={error} onRetry={load} />}
      {adminSuccess && <div role="status" className="mb-4 rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{adminSuccess}</div>}

      {loading ? (
        <Spinner />
      ) : schools.length === 0 ? (
        <Card>
          <EmptyState title="No schools found" hint="Create a school to get started." />
        </Card>
      ) : (
        <Card>
          <Table headers={canManage ? ['Name', 'Code', 'City', 'Country', 'Status', 'School Administrator', 'Actions'] : ['Name', 'Code', 'City', 'Country', 'Status', 'Actions']}>
            {schools.map((s) => (
              <tr key={s.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-900">{s.name}</Td>
                <Td>{s.code}</Td>
                <Td>{s.city ?? '—'}</Td>
                <Td>{s.country ?? '—'}</Td>
                <Td>
                  <Badge tone={s.is_active ? 'green' : 'slate'}>
                    {s.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </Td>
                {canManage && <Td>
                  {(() => {
                    const admin = adminAccounts.find((item) => item.school_id === s.id);
                    if (!admin) return <span className="text-sm text-slate-500">Not configured</span>;
                    return <div className="text-sm"><p className="font-medium text-slate-800">{admin.first_name} {admin.last_name}</p><p className="text-slate-500">{admin.email}</p><p className={admin.is_active ? 'text-emerald-700' : 'text-red-700'}>{admin.is_active ? 'Active' : 'Inactive'}{admin.must_change_password ? ' · Password change required' : ''}</p></div>;
                  })()}
                </Td>}
                <Td>
                  <div className="flex items-center gap-2">
                    {canManage && (
                      <>
                        <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => openEdit(s)}>
                          Edit
                        </Button>
                        {!adminAccounts.some((item) => item.school_id === s.id) && s.is_active && <Button variant="secondary" className="!px-2 !py-1 text-xs" onClick={() => openAdminSetup(s)}>Set Admin</Button>}
                        {s.is_active && (
                          <Button
                            variant="danger"
                            className="!px-2 !py-1 text-xs"
                            onClick={() => handleDeactivate(s)}
                          >
                            Deactivate
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      {/* Create / Edit modal */}
      <Modal
        open={modalOpen}
        title={editingSchool ? 'Edit School' : 'New School'}
        onClose={() => setModalOpen(false)}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Name" required>
              <Input
                required
                value={form.name}
                onChange={(e) => setField('name', e.target.value)}
                placeholder="Springfield High School"
              />
            </Field>
            <Field label="Code" required>
              <Input
                required
                value={form.code}
                onChange={(e) => setField('code', e.target.value)}
                placeholder="SHS"
              />
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Registration Number">
              <Input
                value={form.registration_number ?? ''}
                onChange={(e) => setField('registration_number', e.target.value)}
              />
            </Field>
            <Field label="Phone">
              <Input
                value={form.phone ?? ''}
                onChange={(e) => setField('phone', e.target.value)}
              />
            </Field>
          </div>

          <Field label="Email">
            <Input
              type="email"
              value={form.email ?? ''}
              onChange={(e) => setField('email', e.target.value)}
            />
          </Field>

          <Field label="Address">
            <Input
              value={form.address ?? ''}
              onChange={(e) => setField('address', e.target.value)}
            />
          </Field>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="City">
              <Input
                value={form.city ?? ''}
                onChange={(e) => setField('city', e.target.value)}
              />
            </Field>
            <Field label="Country">
              <Input
                value={form.country ?? ''}
                onChange={(e) => setField('country', e.target.value)}
              />
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Website">
              <Input
                value={form.website ?? ''}
                onChange={(e) => setField('website', e.target.value)}
                placeholder="https://..."
              />
            </Field>
            <Field label="Timezone">
              <Input
                value={form.timezone ?? ''}
                onChange={(e) => setField('timezone', e.target.value)}
                placeholder="Africa/Gaborone"
              />
            </Field>
          </div>

          <Field label="Currency">
            <Input
              value={form.currency ?? ''}
              onChange={(e) => setField('currency', e.target.value)}
              placeholder="BWP"
            />
          </Field>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : editingSchool ? 'Save Changes' : 'Create School'}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={Boolean(creatingAdminFor)} title="Create School Administrator" onClose={() => { if (!adminSaving) setCreatingAdminFor(null); }}>
        <form onSubmit={handleCreateAdmin} className="space-y-4">
          <p className="text-sm text-slate-600">This account will administer only {creatingAdminFor?.name ?? 'this school'}. It cannot access other schools or platform-wide controls. The administrator must change the initial password at first sign-in.</p>
          {adminError && <div role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{adminError}</div>}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="First name" required><Input required value={adminForm.first_name} onChange={(e) => setAdminForm((v) => ({ ...v, first_name: e.target.value }))} /></Field>
            <Field label="Last name" required><Input required value={adminForm.last_name} onChange={(e) => setAdminForm((v) => ({ ...v, last_name: e.target.value }))} /></Field>
          </div>
          <Field label="Administrator email" required><Input type="email" required value={adminForm.email} onChange={(e) => setAdminForm((v) => ({ ...v, email: e.target.value }))} autoComplete="email" /></Field>
          <Field label="Temporary password (12+ characters)" required><Input type="password" required minLength={12} maxLength={128} value={adminForm.password} onChange={(e) => setAdminForm((v) => ({ ...v, password: e.target.value }))} autoComplete="new-password" /></Field>
          <div className="flex justify-end gap-2 pt-2"><Button variant="secondary" type="button" onClick={() => setCreatingAdminFor(null)} disabled={adminSaving}>Cancel</Button><Button type="submit" disabled={adminSaving}>{adminSaving ? 'Creating…' : 'Create School Admin'}</Button></div>
        </form>
      </Modal>
    </div>
  );
}