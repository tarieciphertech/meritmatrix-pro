// Guardians management: list, create, edit, and archive guardians for the
// selected school. Requires a selected school (school_id query param).
// Uses GET/POST /api/v1/guardians?school_id=..., PATCH/DELETE /api/v1/guardians/{id}.

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { GuardianCreate, GuardianResponse, GuardianUpdate } from '../types';
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

const emptyForm: GuardianCreate = {
  first_name: '',
  middle_name: '',
  last_name: '',
  email: '',
  phone: '',
  alternative_phone: '',
  address: '',
  occupation: '',
};

export default function GuardiansPage() {
  const { selectedSchool } = useSchool();
  const [guardians, setGuardians] = useState<GuardianResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingGuardian, setEditingGuardian] = useState<GuardianResponse | null>(null);
  const [form, setForm] = useState<GuardianCreate>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedSchool) {
      setGuardians([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await api.get<GuardianResponse[]>('/api/v1/guardians', {
        school_id: selectedSchool.id,
        limit: 200,
      });
      setGuardians(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load guardians');
    } finally {
      setLoading(false);
    }
  }, [selectedSchool]);

  async function handleCreateAccount(guardian: GuardianResponse) {
    const confirmed = window.confirm(
      `Before generating a login code, confirm you have verified ${guardian.first_name} ${guardian.last_name}'s identity in person. The code will be shown once and expires in 24 hours.`,
    );
    if (!confirmed) return;
    setError(null);
    try {
      const result = await api.post<{
        guardian_name: string;
        phone: string;
        activation_code: string;
        expires_at: string;
        instructions: string;
      }>(`/api/v1/guardian-accounts/${guardian.id}/create`);
      window.alert(
        `Guardian account prepared for ${result.guardian_name}\nPhone: ${result.phone}\n\nONE-TIME ACTIVATION CODE (expires ${new Date(result.expires_at).toLocaleString()}):\n${result.activation_code}\n\nGive this code directly to the verified guardian. They must open /activate-guardian on MeritMatrix Pro and choose their own password. Do not reuse or publish this code.`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create guardian account');
    }
  }

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditingGuardian(null);
    setForm(emptyForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(guardian: GuardianResponse) {
    setEditingGuardian(guardian);
    setForm({
      first_name: guardian.first_name,
      middle_name: guardian.middle_name ?? '',
      last_name: guardian.last_name,
      email: guardian.email ?? '',
      phone: guardian.phone,
      alternative_phone: guardian.alternative_phone ?? '',
      address: guardian.address ?? '',
      occupation: guardian.occupation ?? '',
    });
    setFormError(null);
    setModalOpen(true);
  }

  function setField(key: keyof GuardianCreate, value: string) {
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
      payload.first_name = form.first_name;
      payload.last_name = form.last_name;
      payload.phone = form.phone;

      if (editingGuardian) {
        await api.patch<GuardianResponse>(
          `/api/v1/guardians/${editingGuardian.id}`,
          payload as GuardianUpdate,
        );
      } else {
        await api.post<GuardianResponse>(
          '/api/v1/guardians',
          payload,
          { school_id: selectedSchool.id },
        );
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Failed to save guardian');
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive(guardian: GuardianResponse) {
    if (!window.confirm(`Archive "${guardian.first_name} ${guardian.last_name}"?`)) return;
    try {
      await api.delete<void>(`/api/v1/guardians/${guardian.id}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive guardian');
    }
  }

  if (!selectedSchool) {
    return (
      <div>
        <PageHeader title="Guardians" />
        <Card className="p-6">
          <p className="text-sm text-slate-600">
            Select a school from the header to view and manage guardians.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Guardians"
        subtitle={`Managing guardians for ${selectedSchool.name}`}
        actions={<Button onClick={openCreate}>+ New Guardian</Button>}
      />

      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <Spinner />
      ) : guardians.length === 0 ? (
        <Card>
          <EmptyState title="No guardians found" hint="Add your first guardian to get started." />
        </Card>
      ) : (
        <Card>
          <Table headers={['Name', 'Phone', 'Email', 'Occupation', 'Status', 'Actions']}>
            {guardians.map((g) => (
              <tr key={g.id} className="hover:bg-slate-50">
                <Td className="font-medium text-slate-900">
                  {g.first_name} {g.middle_name ? `${g.middle_name} ` : ''}{g.last_name}
                </Td>
                <Td>{g.phone}</Td>
                <Td>{g.email ?? '—'}</Td>
                <Td>{g.occupation ?? '—'}</Td>
                <Td>
                  <Badge tone={g.is_active ? 'green' : 'slate'}>
                    {g.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </Td>
                <Td>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => openEdit(g)}>
                      Edit
                    </Button>
                    <Button
                      variant="secondary"
                      className="!px-2 !py-1 text-xs"
                      onClick={() => void handleCreateAccount(g)}
                      disabled={!g.is_active}
                    >
                      Create Login
                    </Button>
                    <Button
                      variant="danger"
                      className="!px-2 !py-1 text-xs"
                      onClick={() => handleArchive(g)}
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
        title={editingGuardian ? 'Edit Guardian' : 'New Guardian'}
        onClose={() => setModalOpen(false)}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
              {formError}
            </div>
          )}

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
            <Field label="Phone" required>
              <Input
                required
                value={form.phone}
                onChange={(e) => setField('phone', e.target.value)}
              />
            </Field>
            <Field label="Alternative Phone">
              <Input
                value={form.alternative_phone ?? ''}
                onChange={(e) => setField('alternative_phone', e.target.value)}
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

          <Field label="Occupation">
            <Input
              value={form.occupation ?? ''}
              onChange={(e) => setField('occupation', e.target.value)}
            />
          </Field>

          <Field label="Address">
            <Input
              value={form.address ?? ''}
              onChange={(e) => setField('address', e.target.value)}
            />
          </Field>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : editingGuardian ? 'Save Changes' : 'Create Guardian'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}