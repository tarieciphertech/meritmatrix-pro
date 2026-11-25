import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { useSchool } from '../lib/school-context';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

type Assignment = { id: string; staff_id: string; class_subject_id: string; staff_name: string; class_name: string; class_code: string; subject_name: string; subject_code: string; start_date: string; end_date?: string | null; is_active: boolean };
type Slot = { id: string; staff_id: string; class_subject_id: string; weekday: number; start_time: string; end_time: string; room?: string | null; effective_from: string; effective_to?: string | null; teacher_name: string; class_name: string; class_code: string; subject_name: string; subject_code: string };
type Form = { assignment_id: string; weekday: string; start_time: string; end_time: string; room: string; effective_from: string; effective_to: string };
const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const today = () => { const d = new Date(); return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-'); };
const empty: Form = { assignment_id: '', weekday: '0', start_time: '08:00', end_time: '08:40', room: '', effective_from: today(), effective_to: '' };

export default function TimetablePage() {
  const { user } = useAuth();
  const { selectedSchool } = useSchool();
  const isTeacher = (user?.roles ?? []).some(r => r.name === 'TEACHER');
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [form, setForm] = useState<Form>(empty);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const schoolRef = useRef<string | null>(selectedSchool?.id ?? null);
  const requestRef = useRef(0);
  schoolRef.current = selectedSchool?.id ?? null;

  const load = useCallback(async () => {
    const request = ++requestRef.current;
    if (!selectedSchool) { setSlots([]); setAssignments([]); setLoading(false); return; }
    const schoolId = selectedSchool.id;
    setLoading(true); setError(null);
    try {
      const [slotRows, assignmentRows] = await Promise.all([
        api.get<Slot[]>('/api/v1/timetable', { school_id: schoolId }),
        api.get<Assignment[]>('/api/v1/teaching-assignments', { school_id: schoolId, active_only: true }),
      ]);
      if (schoolRef.current !== schoolId || requestRef.current !== request) return;
      setSlots(slotRows); setAssignments(assignmentRows);
    } catch (e) {
      if (schoolRef.current === schoolId && requestRef.current === request) setError(e instanceof Error ? e.message : 'Could not load timetable');
    } finally {
      if (schoolRef.current === schoolId && requestRef.current === request) setLoading(false);
    }
  }, [selectedSchool]);

  useEffect(() => {
    requestRef.current += 1; setSlots([]); setAssignments([]); setShowForm(false); setError(null); setNotice('');
  }, [selectedSchool?.id]);
  useEffect(() => { void load(); }, [load]);

  const grouped = useMemo(() => weekdays.map((day, index) => ({
    day, items: slots.filter(slot => slot.weekday === index).sort((a,b) => a.start_time.localeCompare(b.start_time)),
  })), [slots]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedSchool) return;
    const assignment = assignments.find(item => item.id === form.assignment_id);
    if (!assignment) { setError('Select an active teaching assignment first.'); return; }
    setSaving(true); setError(null); setNotice('');
    try {
      await api.post('/api/v1/timetable', {
        staff_id: assignment.staff_id, class_subject_id: assignment.class_subject_id,
        weekday: Number(form.weekday), start_time: form.start_time, end_time: form.end_time,
        room: form.room || null, effective_from: form.effective_from, effective_to: form.effective_to || null,
      }, { school_id: selectedSchool.id });
      setForm({ ...empty, effective_from: today() }); setShowForm(false);
      setNotice('Timetable lesson saved.'); await load();
    } catch (e) { setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not save timetable lesson'); }
    finally { setSaving(false); }
  }

  async function remove(slot: Slot) {
    if (!window.confirm(`Remove ${slot.subject_name} from ${slot.class_name} on ${weekdays[slot.weekday]}?`)) return;
    try { await api.delete('/api/v1/timetable/' + slot.id); setNotice('Timetable lesson removed.'); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not remove timetable lesson'); }
  }

  if (!selectedSchool) return <div><PageHeader title="My timetable" /><Card className="p-6">Select a school first.</Card></div>;
  return <div className="space-y-5">
    <PageHeader title={isTeacher ? 'My timetable' : 'Timetable management'} subtitle={isTeacher ? 'Your active weekly teaching schedule.' : `Create and manage weekly lessons for ${selectedSchool.name}.`} actions={!isTeacher ? <Button onClick={() => setShowForm(v => !v)}>{showForm ? 'Cancel' : '+ Add lesson'}</Button> : undefined} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {notice && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    {showForm && !isTeacher && <Card className="p-5"><form onSubmit={submit} className="space-y-4">
      <h2 className="font-semibold text-slate-900">New weekly lesson</h2>
      <label className="block text-sm font-medium">Teacher · class · subject
        <select required value={form.assignment_id} onChange={e => setForm({...form, assignment_id:e.target.value})} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2">
          <option value="">Choose an active teaching assignment…</option>
          {assignments.map(a => <option key={a.id} value={a.id}>{a.staff_name} · {a.class_name} · {a.subject_name}</option>)}
        </select>
      </label>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className="text-sm">Day<select value={form.weekday} onChange={e=>setForm({...form,weekday:e.target.value})} className="mt-1 block w-full rounded-md border p-2">{weekdays.map((d,i)=><option key={d} value={i}>{d}</option>)}</select></label>
        <label className="text-sm">Starts<input required type="time" value={form.start_time} onChange={e=>setForm({...form,start_time:e.target.value})} className="mt-1 block w-full rounded-md border p-2"/></label>
        <label className="text-sm">Ends<input required type="time" min={form.start_time} value={form.end_time} onChange={e=>setForm({...form,end_time:e.target.value})} className="mt-1 block w-full rounded-md border p-2"/></label>
        <label className="text-sm">Room / venue<input value={form.room} onChange={e=>setForm({...form,room:e.target.value})} maxLength={80} className="mt-1 block w-full rounded-md border p-2" placeholder="e.g. Room 4"/></label>
        <label className="text-sm">Effective from<input required type="date" value={form.effective_from} onChange={e=>setForm({...form,effective_from:e.target.value})} className="mt-1 block w-full rounded-md border p-2"/></label>
        <label className="text-sm">Effective to (optional)<input type="date" min={form.effective_from} value={form.effective_to} onChange={e=>setForm({...form,effective_to:e.target.value})} className="mt-1 block w-full rounded-md border p-2"/></label>
      </div>
      <div className="flex justify-end"><Button type="submit" disabled={saving || !assignments.length}>{saving ? 'Saving…' : 'Save lesson'}</Button></div>
      {!assignments.length && <p className="text-sm text-amber-700">Create active teaching assignments before adding timetable lessons.</p>}
    </form></Card>}
    {loading ? <Spinner /> : slots.length === 0 ? <Card className="p-8 text-center"><h2 className="font-semibold text-slate-900">No timetable lessons yet</h2><p className="mt-2 text-sm text-slate-600">{isTeacher ? 'Your school has not published any active lessons for you yet. Ask the school administrator to set up your timetable.' : 'Add lessons using active teacher class-subject assignments. Teachers will see only their own schedule.'}</p></Card> : <div className="grid gap-4 lg:grid-cols-2">
      {grouped.filter(g=>g.items.length>0).map(group=><Card key={group.day} className="overflow-hidden"><div className="border-b border-slate-100 bg-slate-50 px-4 py-3 font-semibold text-slate-800">{group.day}</div><div className="divide-y divide-slate-100">{group.items.map(slot=><div key={slot.id} className="flex items-start justify-between gap-3 p-4"><div className="min-w-0"><p className="font-semibold text-slate-900">{slot.subject_name} <span className="font-normal text-slate-500">· {slot.class_name}</span></p><p className="mt-1 text-sm text-slate-600">{slot.start_time.slice(0,5)}–{slot.end_time.slice(0,5)}{slot.room ? ` · ${slot.room}` : ''}</p>{!isTeacher && <p className="text-xs text-slate-500">{slot.teacher_name}</p>}</div>{!isTeacher && <Button size="sm" variant="danger" onClick={()=>void remove(slot)}>Remove</Button>}</div>)}</div></Card>)}
    </div>}
    <Card className="p-4"><p className="text-sm text-slate-600">Schedules are school-scoped and tied to active teaching assignments. Overlapping lessons for the same teacher or class-subject are rejected. Ending a teaching assignment removes that lesson from the active teacher timetable automatically.</p></Card>
  </div>;
}
