import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api } from '../lib/api';
import { useSchool } from '../lib/school-context';
import { Button, Card, ErrorBanner, Field, Input, Modal, PageHeader, Spinner, Textarea } from '../components/ui';

type Position = {
  id: string; school_id: string; name: string; code: string; description?: string | null;
  is_system: boolean; is_active: boolean; permission_names: string[];
};
type Permission = { name: string; description?: string | null };

export default function SchoolPositionsPage() {
  const { selectedSchool } = useSchool();
  const [positions, setPositions] = useState<Position[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [description, setDescription] = useState('');
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [permissionSearch, setPermissionSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    if (!selectedSchool) { setPositions([]); setPermissions([]); return; }
    setLoading(true); setError(null);
    try {
      const [positionRows, permissionRows] = await Promise.all([
        api.get<Position[]>('/api/v1/school-positions', { school_id: selectedSchool.id }),
        api.get<Permission[]>('/api/v1/school-positions/permissions', { school_id: selectedSchool.id }),
      ]);
      setPositions(positionRows);
      setPermissions(permissionRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load school positions');
    } finally { setLoading(false); }
  }, [selectedSchool]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    setSelectedPosition(null); setModalOpen(false); setNotice(''); setError(null);
  }, [selectedSchool?.id]);

  function openCreate() {
    setSelectedPosition(null); setName(''); setCode(''); setDescription('');
    setSelectedPermissions([]); setPermissionSearch(''); setModalOpen(true);
  }

  function openEdit(position: Position) {
    setSelectedPosition(position); setName(position.name); setCode(position.code);
    setDescription(position.description ?? ''); setSelectedPermissions(position.permission_names);
    setPermissionSearch(''); setModalOpen(true);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!selectedSchool) return;
    setSaving(true); setError(null); setNotice('');
    try {
      if (selectedPosition) {
        await api.patch('/api/v1/school-positions/' + selectedPosition.id, {
          name, description: description || null, permission_names: selectedPermissions,
        }, { school_id: selectedSchool.id } as never);
      } else {
        await api.post('/api/v1/school-positions', {
          name, code, description: description || null, permission_names: selectedPermissions,
        }, { school_id: selectedSchool.id });
      }
      setModalOpen(false);
      setNotice('School position and permissions saved.');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save school position');
    } finally { setSaving(false); }
  }

  const visiblePermissions = permissions.filter(permission =>
    (permission.name + ' ' + (permission.description ?? '')).toLowerCase().includes(permissionSearch.toLowerCase())
  );

  if (!selectedSchool) return <div><PageHeader title="School Positions" /><Card className="p-6">Select a school first.</Card></div>;

  return <div className="space-y-5">
    <PageHeader title="School Positions" subtitle={'Configure school-specific access for ' + selectedSchool.name + '.'} actions={<Button onClick={openCreate}>+ Create position</Button>} />
    {error && <ErrorBanner message={error} onRetry={() => void load()} />}
    {notice && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    {loading ? <Spinner /> : <div className="grid gap-3 md:grid-cols-2">
      {positions.map(position => (
        <Card key={position.id} className="space-y-3 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-slate-900">{position.name}</h2>
              <p className="text-xs uppercase tracking-wide text-slate-500">{position.code}{position.is_system ? ' · Standard position' : ' · Custom position'}</p>
            </div>
            <Button variant="secondary" onClick={() => openEdit(position)}>Configure</Button>
          </div>
          <p className="text-sm text-slate-600">{position.description || 'No description provided.'}</p>
          <p className="text-xs text-slate-500">{position.permission_names.length} permissions assigned</p>
        </Card>
      ))}
    </div>}

    <Card className="p-4">
      <h2 className="font-semibold text-slate-900">How school positions work</h2>
      <p className="mt-1 text-sm text-slate-600">A staff member can hold multiple positions. Their permissions are combined, but they cannot gain platform-wide privileges through a school position. Financial permissions are separated so clerks can capture payments without automatically creating fee charges.</p>
    </Card>

    <Modal open={modalOpen} title={selectedPosition ? 'Configure ' + selectedPosition.name : 'Create school position'} onClose={() => setModalOpen(false)}>
      <form onSubmit={save} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Position name" required><Input required value={name} onChange={event => setName(event.target.value)} /></Field>
          {!selectedPosition && <Field label="Position code" required><Input required value={code} onChange={event => setCode(event.target.value.toUpperCase().replace(/\s+/g, '_'))} placeholder="E.G. LIBRARIAN" /></Field>}
        </div>
        <Field label="Description"><Textarea rows={2} value={description} onChange={event => setDescription(event.target.value)} /></Field>
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-900">Permissions</h3>
            <span className="text-xs text-slate-500">{selectedPermissions.length} selected</span>
          </div>
          <Input value={permissionSearch} onChange={event => setPermissionSearch(event.target.value)} placeholder="Search permissions…" />
          <div className="max-h-72 space-y-1 overflow-y-auto rounded-md border border-slate-200 p-2">
            {visiblePermissions.map(permission => (
              <label key={permission.name} className="flex cursor-pointer items-start gap-2 rounded p-2 hover:bg-slate-50">
                <input type="checkbox" checked={selectedPermissions.includes(permission.name)} onChange={event => setSelectedPermissions(current => event.target.checked ? [...current, permission.name] : current.filter(item => item !== permission.name))} className="mt-1" />
                <span>
                  <span className="block text-sm font-medium text-slate-800">{permission.name}</span>
                  <span className="block text-xs text-slate-500">{permission.description || 'No description'}</span>
                </span>
              </label>
            ))}
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save position'}</Button>
        </div>
      </form>
    </Modal>
  </div>;
}
