import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useSchool } from '../lib/school-context';
import { Badge, Button, Card, ErrorBanner, Input, PageHeader, Select, Spinner } from '../components/ui';
import type { StaffResponse } from '../types';

type Position = { id: string; school_id: string; name: string; code: string; description?: string | null; permissions: string[]; is_system: boolean; is_active: boolean };
type StaffPositions = { staff_id: string; position_ids: string[]; positions: Position[] };

const permissionGroups: { label: string; permissions: { name: string; label: string }[] }[] = [
  { label: 'School and academic setup', permissions: [
    {name:'schools.read',label:'View school'}, {name:'schools.configure',label:'Configure school'},
    {name:'academic_years.read',label:'View academic years'}, {name:'academic_years.create',label:'Create academic years'}, {name:'academic_years.update',label:'Edit academic years'},
    {name:'terms.read',label:'View terms'}, {name:'terms.create',label:'Create terms'}, {name:'terms.update',label:'Edit terms'},
    {name:'classes.read',label:'View classes'}, {name:'classes.create',label:'Create classes'}, {name:'classes.update',label:'Edit classes'},
    {name:'subjects.read',label:'View subjects'}, {name:'subjects.create',label:'Create subjects'}, {name:'subjects.update',label:'Edit subjects'},
    {name:'class_subjects.read',label:'View class subjects'}, {name:'class_subjects.create',label:'Manage timetable and class subjects'}, {name:'class_subjects.delete',label:'Remove timetable lessons'},
  ]},
  { label: 'Students and people', permissions: [
    {name:'students.read',label:'View students'}, {name:'students.create',label:'Register students'}, {name:'students.update',label:'Edit student records'}, {name:'students.delete',label:'Archive students'},
    {name:'guardians.read',label:'View guardians'}, {name:'guardians.create',label:'Add guardians'}, {name:'guardians.update',label:'Edit guardians'}, {name:'guardians.delete',label:'Archive guardians'},
    {name:'student_guardians.read',label:'View guardian links'}, {name:'student_guardians.create',label:'Link guardians'}, {name:'student_guardians.delete',label:'Remove guardian links'},
    {name:'staff.read',label:'View staff'}, {name:'staff.create',label:'Add staff'}, {name:'staff.update',label:'Edit staff and assign positions'}, {name:'staff.delete',label:'Archive staff'},
    {name:'enrollments.read',label:'View enrollments'}, {name:'enrollments.create',label:'Create enrollments'}, {name:'enrollments.update',label:'Edit enrollments'},
  ]},
  { label: 'Teaching and academic records', permissions: [
    {name:'attendance.read',label:'View attendance'}, {name:'attendance.create',label:'Record attendance'},
    {name:'assessments.read',label:'View assessments and marks'}, {name:'assessments.create',label:'Create assessments and record marks'}, {name:'assessments.update',label:'Edit and publish results'},
  ]},
  { label: 'Finance and oversight', permissions: [
    {name:'fees.read',label:'View fees and balances'}, {name:'fees.create',label:'Record financial charges and payments'},
    {name:'audit_logs.read',label:'View audit history'},
  ]},
];

export default function SchoolPositionsPage() {
  const { selectedSchool } = useSchool();
  const [positions, setPositions] = useState<Position[]>([]);
  const [staff, setStaff] = useState<StaffResponse[]>([]);
  const [staffId, setStaffId] = useState('');
  const [assignedIds, setAssignedIds] = useState<string[]>([]);
  const [editing, setEditing] = useState<Position | null>(null);
  const [editPermissions, setEditPermissions] = useState<string[]>([]);
  const [newName, setNewName] = useState('');
  const [newCode, setNewCode] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newPermissions, setNewPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    if (!selectedSchool) { setPositions([]); setStaff([]); return; }
    setLoading(true); setError(null);
    try {
      const [positionRows, staffRows] = await Promise.all([
        api.get<Position[]>('/api/v1/school-positions', { school_id: selectedSchool.id }),
        api.get<StaffResponse[]>('/api/v1/staff', { school_id: selectedSchool.id }),
      ]);
      setPositions(positionRows); setStaff(staffRows);
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load school positions'); }
    finally { setLoading(false); }
  }, [selectedSchool]);

  useEffect(() => { setPositions([]); setStaff([]); setStaffId(''); setAssignedIds([]); setEditing(null); void load(); }, [load, selectedSchool?.id]);

  useEffect(() => {
    if (!staffId) { setAssignedIds([]); return; }
    let cancelled = false;
    api.get<StaffPositions>('/api/v1/school-positions/staff/' + staffId)
      .then(result => { if (!cancelled) setAssignedIds(result.position_ids); })
      .catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : 'Could not load assigned positions'); });
    return () => { cancelled = true; };
  }, [staffId]);

  function toggle(list: string[], value: string, setList: (next: string[]) => void) {
    setList(list.includes(value) ? list.filter(item => item !== value) : [...list, value]);
  }

  async function saveStaffPositions() {
    if (!staffId) return;
    setSaving(true); setError(null); setNotice('');
    try {
      await api.put('/api/v1/school-positions/staff/' + staffId, { position_ids: assignedIds });
      setNotice('School positions assigned. Permissions from all selected positions are combined.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not save staff positions'); }
    finally { setSaving(false); }
  }

  async function savePosition() {
    if (!editing) return;
    setSaving(true); setError(null); setNotice('');
    try {
      const updated = await api.patch<Position>('/api/v1/school-positions/' + editing.id, { permissions: editPermissions });
      setPositions(rows => rows.map(row => row.id === updated.id ? updated : row));
      setEditing(null); setNotice('Position permissions updated.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not update position permissions'); }
    finally { setSaving(false); }
  }

  async function createPosition() {
    if (!selectedSchool) return;
    setSaving(true); setError(null); setNotice('');
    try {
      await api.post('/api/v1/school-positions', {
        name: newName, code: newCode.toUpperCase().replace(/[^A-Z0-9_]/g, '_'),
        description: newDescription, permissions: newPermissions,
      }, { school_id: selectedSchool.id });
      setNewName(''); setNewCode(''); setNewDescription(''); setNewPermissions([]);
      await load(); setNotice('Custom school position created.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not create position'); }
    finally { setSaving(false); }
  }

  if (!selectedSchool) return <div><PageHeader title="School Positions & Permissions" /><Card className="p-6">Select a school first.</Card></div>;

  return <div className="space-y-5">
    <PageHeader title="School Positions & Permissions" subtitle={'Configure position-based access for ' + selectedSchool.name + '. Employees can hold multiple positions.'} />
    {error && <ErrorBanner message={error} onRetry={() => void load()} />}
    {notice && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    {loading ? <Spinner /> : <>
      <Card className="space-y-4 p-5">
        <div><h2 className="font-semibold text-slate-900">Assign positions to an employee</h2><p className="mt-1 text-sm text-slate-600">Select more than one position when an employee performs multiple duties. Their permissions are combined automatically.</p></div>
        <label className="block max-w-xl text-sm font-medium">Staff member
          <Select value={staffId} onChange={e => setStaffId(e.target.value)} className="mt-1">
            <option value="">Choose a staff member…</option>
            {staff.map(person => <option key={person.id} value={person.id}>{person.first_name} {person.last_name} · {person.staff_number}</option>)}
          </Select>
        </label>
        {staffId && <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{positions.map(position => <label key={position.id} className="flex items-start gap-3 rounded-md border border-slate-200 p-3 text-sm"><input type="checkbox" checked={assignedIds.includes(position.id)} onChange={() => toggle(assignedIds, position.id, setAssignedIds)} className="mt-1"/><span><span className="block font-medium text-slate-900">{position.name}</span><span className="text-xs text-slate-500">{position.description}</span></span></label>)}</div>}
        {staffId && <div className="flex justify-end"><Button onClick={() => void saveStaffPositions()} disabled={saving}>{saving ? 'Saving…' : 'Save employee positions'}</Button></div>}
      </Card>
      <Card className="space-y-4 p-5">
        <div><h2 className="font-semibold text-slate-900">Standard school positions</h2><p className="mt-1 text-sm text-slate-600">These are permission templates. Customize them to match the school's actual responsibilities.</p></div>
        <div className="divide-y divide-slate-100">{positions.map(position => <div key={position.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><div className="flex flex-wrap items-center gap-2"><span className="font-medium text-slate-900">{position.name}</span>{position.is_system && <Badge tone="indigo">Standard</Badge>}</div><p className="mt-1 text-xs text-slate-500">{position.description} · {position.permissions.length} permissions</p></div><Button variant="secondary" onClick={() => { setEditing(position); setEditPermissions(position.permissions); }}>Configure permissions</Button></div>)}</div>
      </Card>
      <Card className="space-y-4 p-5">
        <div><h2 className="font-semibold text-slate-900">Create a custom position</h2><p className="mt-1 text-sm text-slate-600">Create additional school positions without granting platform-wide administrator rights.</p></div>
        <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm">Position name<Input value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Examination Officer" /></label><label className="text-sm">Position code<Input value={newCode} onChange={e => setNewCode(e.target.value)} placeholder="EXAM_OFFICER" /></label></div>
        <label className="block text-sm">Description<Input value={newDescription} onChange={e => setNewDescription(e.target.value)} placeholder="Responsibilities of this position" /></label>
        <div className="grid gap-3 sm:grid-cols-2">{permissionGroups.map(group => <div key={group.label}><h3 className="mb-2 text-sm font-semibold text-slate-800">{group.label}</h3><div className="space-y-2">{group.permissions.map(permission => <label key={permission.name} className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={newPermissions.includes(permission.name)} onChange={() => toggle(newPermissions, permission.name, setNewPermissions)} />{permission.label}</label>)}</div></div>)}</div>
        <div className="flex justify-end"><Button onClick={() => void createPosition()} disabled={saving || newName.trim().length < 2 || newCode.trim().length < 2}>{saving ? 'Creating…' : 'Create custom position'}</Button></div>
      </Card>
    </>}
    {editing && <Card className="space-y-4 border-2 border-indigo-200 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-semibold text-slate-900">Configure {editing.name}</h2><p className="text-sm text-slate-500">Changes apply to every employee assigned this position.</p></div><Button variant="secondary" onClick={() => setEditing(null)}>Close</Button></div>
      <div className="grid gap-3 sm:grid-cols-2">{permissionGroups.map(group => <div key={group.label}><h3 className="mb-2 text-sm font-semibold text-slate-800">{group.label}</h3><div className="space-y-2">{group.permissions.map(permission => <label key={permission.name} className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={editPermissions.includes(permission.name)} onChange={() => toggle(editPermissions, permission.name, setEditPermissions)} />{permission.label}</label>)}</div></div>)}</div>
      <div className="flex justify-end"><Button onClick={() => void savePosition()} disabled={saving}>{saving ? 'Saving…' : 'Save permission template'}</Button></div>
    </Card>}
  </div>;
}
