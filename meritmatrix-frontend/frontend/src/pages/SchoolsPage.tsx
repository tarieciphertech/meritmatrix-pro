// Schools management: list, create, edit, and deactivate schools.
// Uses GET /api/v1/schools, POST /api/v1/schools, PATCH /api/v1/schools/{id},
// DELETE /api/v1/schools/{id} (deactivate).

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { INSTITUTION_TYPES, type InstitutionType, type SchoolCreate, type SchoolResponse, type SchoolUpdate } from '../types';
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
  country_code: 'ZW',
  institution_type: 'secondary',
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
  const [logoLoading, setLogoLoading] = useState(false);
  const [logoLoadFailed, setLogoLoadFailed] = useState(false);
  const [logoTouched, setLogoTouched] = useState(false);
  const logoRequestId = useRef(0);
  const [formError, setFormError] = useState<string | null>(null);
  const [adminAccounts, setAdminAccounts] = useState<SchoolAdminStatus[]>([]);
  const [creatingAdminFor, setCreatingAdminFor] = useState<SchoolResponse | null>(null);
  const [adminForm, setAdminForm] = useState<SchoolAdminForm>(emptyAdminForm);
  const [adminSaving, setAdminSaving] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [adminSuccess, setAdminSuccess] = useState<string | null>(null);
  const [resettingAdminFor, setResettingAdminFor] = useState<SchoolResponse | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [resetSaving, setResetSaving] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  const canManage = hasRole('SUPER_ADMIN');
  const canConfigureSchool = canManage || hasRole('SCHOOL_ADMIN');

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
    logoRequestId.current += 1;
    setLogoLoading(false);
    setLogoLoadFailed(false);
    setLogoTouched(false);
    setEditingSchool(null);
    setForm(emptyForm);
    setAdminForm(emptyAdminForm);
    setFormError(null);
    setModalOpen(true);
  }

  async function openEdit(school: SchoolResponse) {
    const requestId = ++logoRequestId.current;
    setLogoLoading(true);
    setLogoLoadFailed(false);
    setLogoTouched(false);
    setEditingSchool(school);
    setForm({
      name: school.name,
      code: school.code,
      registration_number: school.registration_number ?? '',
      address: school.address ?? '',
      city: school.city ?? '',
      country: school.country ?? '',
      country_code: school.country_code ?? undefined,
      institution_type: school.institution_type ?? undefined,
      phone: school.phone ?? '',
      email: school.email ?? '',
      website: school.website ?? '',
      logo_url: school.logo_url ?? '',
      timezone: school.timezone ?? '',
      currency: school.currency ?? '',
    });
    setFormError(null);
    setModalOpen(true);
    try {
      // List responses intentionally omit embedded data-URI logos to stay small.
      // Fetch the selected school's logo separately so editing other fields never
      // accidentally clears its existing logo.
      const result = await api.get<{ logo_url: string | null }>(`/api/v1/schools/${school.id}/logo`);
      if (logoRequestId.current === requestId) {
        setForm((current) => ({ ...current, logo_url: result.logo_url ?? '' }));
        setLogoLoadFailed(false);
      }
    } catch {
      if (logoRequestId.current === requestId) {
        setLogoLoadFailed(true);
        setForm((current) => ({ ...current, logo_url: school.logo_url ?? '' }));
      }
    } finally {
      if (logoRequestId.current === requestId) setLogoLoading(false);
    }
  }

  function setField(key: keyof SchoolCreate, value: string) {
    if (key === 'logo_url') { setLogoTouched(true); setLogoLoadFailed(false); }
    setForm((prev) => ({ ...prev, [key]: value } as SchoolCreate));
  }

  function handleLogoUpload(file?: File) {
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      setFormError('Use a PNG, JPEG, or WebP school logo.');
      return;
    }
    if (file.size > 256 * 1024) {
      setFormError('School logos must be 256 KB or smaller.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== 'string') {
        setFormError('Could not read that logo file. Try another image.');
        return;
      }
      setForm((prev) => ({ ...prev, logo_url: reader.result as string }));
      setLogoTouched(true);
      setLogoLoadFailed(false);
      setFormError(null);
    };
    reader.onerror = () => setFormError('Could not read that logo file. Try another image.');
    reader.readAsDataURL(file);
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
      // If the logo endpoint failed, preserve the current database value unless
      // the user explicitly selected or removed a logo in this editing session.
      if (editingSchool && logoLoadFailed && !logoTouched) delete payload.logo_url;

      if (editingSchool) {
        // School administrators may update only school-specific configuration.
        // Never send platform identity fields (name/code) from their form because
        // the API deliberately rejects attempts to change those fields.
        const updatePayload: SchoolUpdate = canManage
          ? { ...payload }
          : Object.fromEntries(
              Object.entries(payload).filter(([key]) => !['name', 'code'].includes(key)),
            ) as SchoolUpdate;
        await api.patch<SchoolResponse>(`/api/v1/schools/${editingSchool.id}`, updatePayload);
      } else {
        if (!adminForm.first_name.trim() || !adminForm.last_name.trim() || !adminForm.email.trim()) {
          setFormError('Enter the first school administrator details before creating the school.');
          setSaving(false);
          return;
        }
        if (adminForm.password.length < 12) {
          setFormError('The school administrator temporary password must be at least 12 characters.');
          setSaving(false);
          return;
        }
        const result = await api.post<{ school: SchoolResponse; admin: { email: string; school_name: string } }>(
          '/api/v1/schools/onboard',
          { school: payload, admin: adminForm },
        );
        setAdminSuccess(`Created ${result.school.name} and its school administrator (${result.admin.email}). The administrator must change the temporary password at first sign-in.`);
        setAdminForm(emptyAdminForm);
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

  async function handleResetAdminPassword(e: FormEvent) {
    e.preventDefault();
    if (!resettingAdminFor) return;
    if (resetPassword.length < 12) {
      setResetError('Use a temporary password of at least 12 characters.');
      return;
    }
    setResetSaving(true);
    setResetError(null);
    try {
      const result = await api.post<{ school_name: string; email: string; must_change_password: boolean }>(
        `/api/v1/schools/${resettingAdminFor.id}/admin-account/reset-password`,
        { password: resetPassword },
      );
      setAdminSuccess(`Login reset for ${result.school_name} (${result.email}). All existing sessions were revoked; the administrator must change the temporary password at next sign-in.`);
      setResettingAdminFor(null);
      setResetPassword('');
      await load();
    } catch (err) {
      setResetError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Could not reset the school administrator login.');
    } finally {
      setResetSaving(false);
    }
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
        subtitle={canManage ? 'Manage schools, school administrators, and platform-level settings.' : 'Manage configuration and branding for your assigned school.'}
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
                    return <div className="space-y-2 text-sm"><p className="font-medium text-slate-800">{admin.first_name} {admin.last_name}</p><p className="text-slate-500">{admin.email}</p><p className={admin.is_active ? 'text-emerald-700' : 'text-red-700'}>{admin.is_active ? 'Active' : 'Inactive'}{admin.must_change_password ? ' · Password change required' : ''}</p>{admin.is_active && <Button variant="secondary" className="!px-2 !py-1 text-xs" onClick={() => { setResettingAdminFor(s); setResetPassword(''); setResetError(null); }}>Reset login</Button>}</div>;
                  })()}
                </Td>}
                <Td>
                  <div className="flex items-center gap-2">
                    {canConfigureSchool && (
                      <>
                        <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => openEdit(s)}>
                          {canManage ? 'Edit' : 'Configure'}
                        </Button>
                        {canManage && !adminAccounts.some((item) => item.school_id === s.id) && s.is_active && <Button variant="secondary" className="!px-2 !py-1 text-xs" onClick={() => openAdminSetup(s)}>Set Admin</Button>}
                        {canManage && s.is_active && (
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
        title={editingSchool ? (canManage ? 'Edit School' : 'School Configuration') : 'New School'}
        onClose={() => { logoRequestId.current += 1; setLogoLoading(false); setModalOpen(false); }}
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
                disabled={Boolean(editingSchool) && !canManage}
                value={form.name}
                onChange={(e) => setField('name', e.target.value)}
                placeholder="Springfield High School"
              />
            </Field>
            <Field label="Code" required>
              <Input
                required
                disabled={Boolean(editingSchool) && !canManage}
                value={form.code}
                onChange={(e) => setField('code', e.target.value)}
                placeholder="SHS"
              />
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Institution type" required>
              <select required value={form.institution_type ?? ''} onChange={(e) => setField('institution_type', e.target.value as InstitutionType)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm">
                <option value="">Choose school type…</option>
                {INSTITUTION_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
              </select>
            </Field>
            <Field label="Country">
              <select value={form.country_code ?? ''} onChange={(e) => { const code = e.target.value; setForm((prev) => ({ ...prev, country_code: code as SchoolCreate['country_code'], country: code === 'ZW' ? 'Zimbabwe' : code === 'BW' ? 'Botswana' : prev.country })); }} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm">
                <option value="">Choose country…</option><option value="ZW">Zimbabwe</option><option value="BW">Botswana</option>
              </select>
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

          <Field label="City">
            <Input
              value={form.city ?? ''}
              onChange={(e) => setField('city', e.target.value)}
            />
          </Field>

          <div className="space-y-3 rounded-lg border border-slate-200 p-3">
            <Field label="Upload school logo">
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => { handleLogoUpload(e.target.files?.[0]); e.currentTarget.value = ''; }}
                className="block w-full text-sm"
              />
              <p className="mt-1 text-xs text-slate-500">PNG, JPEG, or WebP; maximum 256 KB. The logo is saved with this school and printed with its name on report cards.</p>
            </Field>
            <Field label="Or use a public logo URL">
              <Input
                type="url"
                value={(form.logo_url ?? '').startsWith('data:image/') ? '' : (form.logo_url ?? '')}
                onChange={(e) => setField('logo_url', e.target.value)}
                placeholder="https://example.com/school-logo.png"
              />
            </Field>
            {form.logo_url && (
              <div className="flex items-center gap-3 rounded-md bg-slate-50 p-3">
                <img
                  src={form.logo_url}
                  alt={(form.name.trim() || 'School') + ' logo preview'}
                  className="h-16 w-16 shrink-0 object-contain"
                  onError={(event) => { event.currentTarget.style.display = 'none'; }}
                />
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-slate-900">{form.name.trim() || 'School name preview'}</p>
                  <p className="text-xs text-slate-600">This logo and school name will appear together on printed report cards.</p>
                </div>
                <Button type="button" variant="secondary" onClick={() => setField('logo_url', '')}>Remove logo</Button>
              </div>
            )}
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

          {!editingSchool && (
            <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div>
                <h3 className="font-semibold text-slate-900">First school administrator</h3>
                <p className="mt-1 text-sm text-slate-600">Every new school is created with its own administrator account. This account can manage only this school and must change its temporary password at first sign-in.</p>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Administrator first name" required>
                  <Input required value={adminForm.first_name} onChange={(e) => setAdminForm((v) => ({ ...v, first_name: e.target.value }))} autoComplete="given-name" />
                </Field>
                <Field label="Administrator last name" required>
                  <Input required value={adminForm.last_name} onChange={(e) => setAdminForm((v) => ({ ...v, last_name: e.target.value }))} autoComplete="family-name" />
                </Field>
              </div>
              <Field label="Administrator email / login" required>
                <Input type="email" required value={adminForm.email} onChange={(e) => setAdminForm((v) => ({ ...v, email: e.target.value }))} autoComplete="email" />
              </Field>
              <Field label="Temporary password (12+ characters)" required>
                <Input type="password" required minLength={12} maxLength={128} value={adminForm.password} onChange={(e) => setAdminForm((v) => ({ ...v, password: e.target.value }))} autoComplete="new-password" />
              </Field>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || logoLoading}>
              {logoLoading ? 'Loading school logo…' : saving ? 'Saving…' : editingSchool ? (canManage ? 'Save Changes' : 'Save School Configuration') : 'Create School'}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={Boolean(resettingAdminFor)} title="Reset School Administrator Login" onClose={() => { if (!resetSaving) { setResettingAdminFor(null); setResetPassword(''); setResetError(null); } }}>
        <form onSubmit={handleResetAdminPassword} className="space-y-4">
          <p className="text-sm text-slate-600">Reset the administrator password for {resettingAdminFor?.name ?? 'this school'}. All current sessions for that account will be revoked, and the administrator will be required to choose a new password at next sign-in.</p>
          {resetError && <div role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{resetError}</div>}
          <Field label="Temporary password (12+ characters)" required>
            <Input type="password" required minLength={12} maxLength={128} value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} autoComplete="new-password" />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" type="button" onClick={() => { setResettingAdminFor(null); setResetPassword(''); setResetError(null); }} disabled={resetSaving}>Cancel</Button>
            <Button type="submit" disabled={resetSaving}>{resetSaving ? 'Resetting…' : 'Reset administrator login'}</Button>
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