import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { useSchool } from '../lib/school-context';
import { Badge, Button, Card, ErrorBanner, PageHeader, Select, Spinner } from '../components/ui';
import type { AcademicYearResponse } from '../types';

type Assignment = { id: string; staff_id: string; class_subject_id: string; staff_name: string; class_name: string; class_code: string; subject_name: string; subject_code: string; start_date: string; end_date?: string | null; is_active: boolean };
type Annual = { id: string; school_id: string; academic_year_id: string; academic_year_name: string; academic_year_start: string; academic_year_end: string; status: 'draft' | 'published'; version: number; published_at?: string | null };
type Slot = { id: string; annual_timetable_id?: string | null; staff_id: string; class_subject_id: string; weekday: number; start_time: string; end_time: string; room?: string | null; effective_from: string; effective_to?: string | null; teacher_name: string; class_name: string; class_code: string; subject_name: string; subject_code: string };
type Form = { assignment_id: string; weekday: string; start_time: string; end_time: string; room: string };
const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const blank: Form = { assignment_id: '', weekday: '0', start_time: '08:00', end_time: '08:40', room: '' };

export default function TimetablePage() {
  const { user } = useAuth();
  const { selectedSchool } = useSchool();
  const isTeacher = (user?.roles ?? []).some(r => r.name === 'TEACHER');
  const [years, setYears] = useState<AcademicYearResponse[]>([]);
  const [annuals, setAnnuals] = useState<Annual[]>([]);
  const [annualId, setAnnualId] = useState('');
  const [yearId, setYearId] = useState('');
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [form, setForm] = useState<Form>(blank);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const schoolRef = useRef<string | null>(selectedSchool?.id ?? null);
  const requestRef = useRef(0);
  schoolRef.current = selectedSchool?.id ?? null;

  const selectedAnnual = annuals.find(item => item.id === annualId) ?? null;
  const grouped = useMemo(() => weekdays.map((day, index) => ({
    day, items: slots.filter(slot => slot.weekday === index).sort((a, b) => a.start_time.localeCompare(b.start_time)),
  })), [slots]);

  const load = useCallback(async () => {
    const request = ++requestRef.current;
    if (!selectedSchool) {
      setYears([]); setAnnuals([]); setAssignments([]); setSlots([]); setLoading(false);
      return;
    }
    const schoolId = selectedSchool.id;
    setLoading(true); setError(null);
    try {
      const [yearRows, annualRows, assignmentRows] = await Promise.all([
        api.get<AcademicYearResponse[]>('/api/v1/academic-years', { school_id: schoolId }),
        api.get<Annual[]>('/api/v1/timetable/annual', { school_id: schoolId }),
        api.get<Assignment[]>('/api/v1/teaching-assignments', { school_id: schoolId, active_only: true }),
      ]);
      if (schoolRef.current !== schoolId || requestRef.current !== request) return;
      setYears(yearRows); setAnnuals(annualRows); setAssignments(assignmentRows);
      const preferredYear = yearRows.find(y => y.is_current) ?? yearRows[0];
      const preferredAnnual = annualRows.find(a => a.academic_year_id === (yearId || preferredYear?.id))
        ?? annualRows.find(a => a.academic_year_id === preferredYear?.id) ?? annualRows[0];
      if (!yearId && preferredYear) setYearId(preferredYear.id);
      if (!annualId && preferredAnnual) setAnnualId(preferredAnnual.id);
      const activeAnnualId = annualId || preferredAnnual?.id || '';
      if (activeAnnualId) {
        const rows = await api.get<Slot[]>('/api/v1/timetable', {
          school_id: schoolId, annual_timetable_id: activeAnnualId,
          active_on: annualRows.find(a => a.id === activeAnnualId)?.academic_year_start ?? preferredYear?.start_date,
        });
        if (schoolRef.current === schoolId && requestRef.current === request) setSlots(rows);
      } else {
        setSlots([]);
      }
    } catch (e) {
      if (schoolRef.current === schoolId && requestRef.current === request) setError(e instanceof Error ? e.message : 'Could not load annual timetable');
    } finally {
      if (schoolRef.current === schoolId && requestRef.current === request) setLoading(false);
    }
  }, [selectedSchool, yearId, annualId]);

  useEffect(() => {
    requestRef.current += 1;
    setYears([]); setAnnuals([]); setAssignments([]); setSlots([]);
    setAnnualId(''); setYearId(''); setShowForm(false); setError(null); setNotice('');
  }, [selectedSchool?.id]);
  useEffect(() => { void load(); }, [load]);

  async function createAnnual() {
    if (!selectedSchool || !yearId) return;
    setSaving(true); setError(null); setNotice('');
    try {
      const created = await api.post<Annual>('/api/v1/timetable/annual', { academic_year_id: yearId }, { school_id: selectedSchool.id });
      setAnnuals(current => [...current, created]); setAnnualId(created.id); setSlots([]);
      setNotice('Annual master timetable created. Add the school’s recurring weekly lessons, then publish it.');
    } catch (e) { setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not create annual timetable'); }
    finally { setSaving(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedSchool || !selectedAnnual) return;
    const assignment = assignments.find(item => item.id === form.assignment_id);
    if (!assignment) { setError('Select an active teacher, class and subject assignment.'); return; }
    setSaving(true); setError(null); setNotice('');
    try {
      await api.post('/api/v1/timetable', {
        annual_timetable_id: selectedAnnual.id,
        staff_id: assignment.staff_id, class_subject_id: assignment.class_subject_id,
        weekday: Number(form.weekday), start_time: form.start_time, end_time: form.end_time,
        room: form.room.trim() || null,
        effective_from: selectedAnnual.academic_year_start,
        effective_to: selectedAnnual.academic_year_end,
      }, { school_id: selectedSchool.id });
      setForm(blank); setShowForm(false);
      setNotice('Lesson added to the annual master timetable. Teacher, class and room availability were checked.');
      await load();
    } catch (e) { setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not save timetable lesson'); }
    finally { setSaving(false); }
  }

  async function publish() {
    if (!selectedAnnual) return;
    if (!window.confirm('Publish this annual master timetable? Teachers will see it as the approved school timetable.')) return;
    setSaving(true); setError(null);
    try {
      const updated = await api.post<Annual>('/api/v1/timetable/annual/' + selectedAnnual.id + '/publish');
      setAnnuals(rows => rows.map(row => row.id === updated.id ? updated : row));
      setNotice('Annual master timetable published.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not publish timetable'); }
    finally { setSaving(false); }
  }

  async function reopen() {
    if (!selectedAnnual) return;
    if (!window.confirm('Reopen this published timetable for an authorized amendment? This creates a new timetable version.')) return;
    setSaving(true); setError(null);
    try {
      const updated = await api.post<Annual>('/api/v1/timetable/annual/' + selectedAnnual.id + '/reopen');
      setAnnuals(rows => rows.map(row => row.id === updated.id ? updated : row));
      setNotice('Timetable reopened for amendment. The new version is ' + updated.version + '.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not reopen timetable'); }
    finally { setSaving(false); }
  }

  async function remove(slot: Slot) {
    if (!window.confirm('Remove ' + slot.subject_name + ' from ' + slot.class_name + ' on ' + weekdays[slot.weekday] + '?')) return;
    try { await api.delete('/api/v1/timetable/' + slot.id); setNotice('Lesson removed from the draft timetable.'); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not remove timetable lesson'); }
  }

  if (!selectedSchool) return <div><PageHeader title="My timetable" /><Card className="p-6">Select a school first.</Card></div>;

  const availableYears = years.filter(y => y.is_active);
  return <div className="space-y-5">
    <PageHeader title={isTeacher ? 'My timetable' : 'Annual Master Timetable'} subtitle={isTeacher ? 'Your approved recurring weekly schedule for the academic year.' : 'Build, validate and publish one recurring weekly timetable for the full academic year at ' + selectedSchool.name + '.'} />
    {error && <ErrorBanner message={error} onRetry={() => void load()} />}
    {notice && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    <Card className="space-y-4 p-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-700">Academic year
          <Select value={selectedAnnual?.academic_year_id ?? yearId} onChange={e => {
            setYearId(e.target.value);
            const match = annuals.find(a => a.academic_year_id === e.target.value);
            setAnnualId(match?.id ?? '');
          }} className="mt-1">
            <option value="">Choose academic year…</option>
            {availableYears.map(y => <option key={y.id} value={y.id}>{y.name} ({y.start_date} – {y.end_date})</option>)}
          </Select>
        </label>
        <div className="flex items-end gap-2">
          {selectedAnnual ? <>
            <Badge tone={selectedAnnual.status === 'published' ? 'green' : 'amber'}>{selectedAnnual.status === 'published' ? 'Published' : 'Draft'} · v{selectedAnnual.version}</Badge>
            {!isTeacher && selectedAnnual.status === 'draft' && <Button onClick={() => void publish()} disabled={saving || slots.length === 0}>Publish timetable</Button>}
            {!isTeacher && selectedAnnual.status === 'published' && <Button variant="secondary" onClick={() => void reopen()} disabled={saving}>Reopen for amendment</Button>}
          </> : !isTeacher && yearId && <Button onClick={() => void createAnnual()} disabled={saving}>{saving ? 'Creating…' : 'Create annual master'}</Button>}
        </div>
      </div>
      {selectedAnnual && <p className="text-sm text-slate-600">This master timetable applies from {selectedAnnual.academic_year_start} to {selectedAnnual.academic_year_end}. Term dates, holidays and special events do not require rebuilding the weekly timetable.</p>}
    </Card>
    {!isTeacher && selectedAnnual?.status === 'draft' && <div className="flex justify-end"><Button onClick={() => setShowForm(value => !value)}>{showForm ? 'Cancel' : '+ Add lesson'}</Button></div>}
    {showForm && !isTeacher && selectedAnnual?.status === 'draft' && <Card className="p-5">
      <form onSubmit={submit} className="space-y-4">
        <h2 className="font-semibold text-slate-900">Add recurring weekly lesson</h2>
        <label className="block text-sm font-medium">Teacher · class · subject
          <Select required value={form.assignment_id} onChange={e => setForm({ ...form, assignment_id: e.target.value })}>
            <option value="">Choose an active teaching assignment…</option>
            {assignments.map(a => <option key={a.id} value={a.id}>{a.staff_name} · {a.class_name} · {a.subject_name}</option>)}
          </Select>
        </label>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-sm">Day<Select value={form.weekday} onChange={e => setForm({ ...form, weekday: e.target.value })}>{weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}</Select></label>
          <label className="text-sm">Starts<input required type="time" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })} className="mt-1 block w-full rounded-md border border-slate-300 p-2" /></label>
          <label className="text-sm">Ends<input required type="time" min={form.start_time} value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })} className="mt-1 block w-full rounded-md border border-slate-300 p-2" /></label>
          <label className="text-sm">Room / venue<input value={form.room} onChange={e => setForm({ ...form, room: e.target.value })} maxLength={80} className="mt-1 block w-full rounded-md border border-slate-300 p-2" placeholder="e.g. Room 4" /></label>
        </div>
        <p className="text-xs text-slate-500">The lesson repeats weekly for the entire academic year. The system rejects teacher, class and room clashes before saving.</p>
        <div className="flex justify-end"><Button type="submit" disabled={saving || !assignments.length}>{saving ? 'Saving…' : 'Add to master timetable'}</Button></div>
        {!assignments.length && <p className="text-sm text-amber-700">Create active teaching assignments before scheduling lessons.</p>}
      </form>
    </Card>}
    {loading ? <Spinner /> : !selectedAnnual ? <Card className="p-8 text-center"><h2 className="font-semibold text-slate-900">No annual master timetable selected</h2><p className="mt-2 text-sm text-slate-600">{isTeacher ? 'The school has not published an annual timetable for this academic year yet.' : 'Choose an academic year and create its annual master timetable to begin.'}</p></Card> : slots.length === 0 ? <Card className="p-8 text-center"><h2 className="font-semibold text-slate-900">No lessons in this timetable yet</h2><p className="mt-2 text-sm text-slate-600">{isTeacher ? 'No lessons have been published for your account in this academic year.' : 'Add recurring weekly lessons. Every lesson is checked against the teacher, entire class and room schedule.'}</p></Card> : <div className="grid gap-4 lg:grid-cols-2">
      {grouped.filter(group => group.items.length > 0).map(group => <Card key={group.day} className="overflow-hidden"><div className="border-b border-slate-100 bg-slate-50 px-4 py-3 font-semibold text-slate-800">{group.day}</div><div className="divide-y divide-slate-100">{group.items.map(slot => <div key={slot.id} className="flex items-start justify-between gap-3 p-4"><div className="min-w-0"><p className="font-semibold text-slate-900">{slot.subject_name} <span className="font-normal text-slate-500">· {slot.class_name}</span></p><p className="mt-1 text-sm text-slate-600">{slot.start_time.slice(0, 5)}–{slot.end_time.slice(0, 5)}{slot.room ? ' · ' + slot.room : ''}</p>{!isTeacher && <p className="text-xs text-slate-500">{slot.teacher_name}</p>}</div>{!isTeacher && selectedAnnual.status === 'draft' && <Button variant="danger" onClick={() => void remove(slot)}>Remove</Button>}</div>)}</div></Card>)}
    </div>}
    <Card className="p-4"><p className="text-sm text-slate-600">One master timetable applies for the full academic year. Published schedules are locked; authorized amendments reopen a new version and are recorded in the school audit history. Temporary examinations, holidays and events remain date-specific calendar exceptions.</p></Card>
  </div>;
}
