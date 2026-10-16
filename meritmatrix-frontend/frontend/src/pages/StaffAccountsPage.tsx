import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { StaffResponse } from '../types';
import { Button, Card, ErrorBanner, Field, Input, PageHeader, Spinner } from '../components/ui';

export default function StaffAccountsPage() {
  const { selectedSchool } = useSchool();
  const [staff, setStaff] = useState<StaffResponse[]>([]);
  const [passwords, setPasswords] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedSchool) { setStaff([]); return; }
    setLoading(true); setError(null);
    try {
      const rows = await api.get<StaffResponse[]>('/api/v1/staff', { school_id: selectedSchool.id, limit: 200 });
      setStaff(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load staff.');
    } finally { setLoading(false); }
  }, [selectedSchool]);

  useEffect(() => { void load(); }, [load]);

  async function createAccount(person: StaffResponse) {
    const password = passwords[person.id] ?? '';
    if (password.length < 12) { setError('Use an initial password with at least 12 characters.'); return; }
    setBusyId(person.id); setError(null); setNotice(null);
    try {
      const result = await api.post<{ email: string; role: string; message: string }>(
        `/api/v1/staff/${person.id}/login-account`, { password },
      );
      setPasswords((current) => ({ ...current, [person.id]: '' }));
      setNotice(`Login created for ${result.email} with role ${result.role}. ${result.message}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to create the login account.');
    } finally { setBusyId(null); }
  }

  return <div>
    <PageHeader title="Staff Login Access" subtitle={selectedSchool ? `Provision login accounts for staff at ${selectedSchool.name}` : 'Select a school to manage staff login access.'} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {notice && <div role="status" className="mb-4 rounded-md bg-green-50 px-4 py-3 text-sm text-green-800 ring-1 ring-green-200">{notice}</div>}
    {!selectedSchool ? <Card className="p-6"><p className="text-sm text-slate-600">Select a school from the header to continue.</p></Card> :
      loading ? <Spinner /> : staff.length === 0 ? <Card className="p-6"><p className="text-sm text-slate-600">No staff records found. Add staff first, and ensure each staff member has a unique email address.</p></Card> :
      <div className="space-y-3">{staff.map((person) => {
        const eligible = person.is_active && person.employment_status === 'active' && !!person.email;
        return <Card key={person.id} className="p-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="min-w-0">
              <h2 className="font-semibold text-slate-900">{person.first_name} {person.last_name}</h2>
              <p className="text-sm text-slate-600">{person.job_title || 'Staff'} · Staff #{person.staff_number}</p>
              <p className="text-sm text-slate-500">{person.email || 'No email address on record'}</p>
              {!eligible && <p className="mt-1 text-xs text-amber-700">Requires active employment and an email address before login can be created.</p>}
            </div>
            <div className="w-full max-w-md space-y-2">
              <Field label="Initial password (12+ characters)">
                <Input type="password" autoComplete="new-password" value={passwords[person.id] ?? ''} onChange={(e) => setPasswords((current) => ({ ...current, [person.id]: e.target.value }))} placeholder="Set a temporary password" />
              </Field>
              <Button disabled={!eligible || busyId === person.id || (passwords[person.id] ?? '').length < 12} onClick={() => void createAccount(person)}>
                {busyId === person.id ? 'Creating…' : 'Create teacher login'}
              </Button>
              <p className="text-xs text-slate-500">Least-privilege access: TEACHER role, limited to this school. Never reuse an administrator password.</p>
            </div>
          </div>
        </Card>;
      })}</div>}
  </div>;
}
