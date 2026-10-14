import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

type EventType = 'public_holiday' | 'school_holiday' | 'term' | 'exam_period' | 'school_closure' | 'school_event';
type EventSource = 'government' | 'school' | 'exam_board' | 'other';
type CalendarEvent = { id: string; school_id: string; title: string; event_type: EventType; start_date: string; end_date: string; is_instructional: boolean; source: EventSource; source_url?: string | null; is_approved: boolean; notes?: string | null; };
type EventForm = { title: string; event_type: EventType; start_date: string; end_date: string; is_instructional: boolean; source: EventSource; source_url: string; notes: string; };
const blank: EventForm = { title: '', event_type: 'school_event', start_date: '', end_date: '', is_instructional: true, source: 'school', source_url: '', notes: '' };
const eventTypes: {value: EventType; label: string}[] = [
  { value: 'public_holiday', label: 'Public holiday' }, { value: 'school_holiday', label: 'School holiday' },
  { value: 'term', label: 'Term / semester' }, { value: 'exam_period', label: 'Examination period' },
  { value: 'school_closure', label: 'School closure' }, { value: 'school_event', label: 'School event' },
];

export default function SchoolCalendarPage() {
  const { selectedSchool } = useSchool();
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [form, setForm] = useState<EventForm>(blank);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    if (!selectedSchool) { setEvents([]); return; }
    setLoading(true); setError(null);
    try { setEvents(await api.get<CalendarEvent[]>('/api/v1/calendar-events', { school_id: selectedSchool.id })); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not load school calendar'); }
    finally { setLoading(false); }
  }, [selectedSchool]);
  useEffect(() => { void load(); }, [load]);

  function change<K extends keyof EventForm>(key: K, value: EventForm[K]) {
    setForm((old) => ({ ...old, [key]: value }));
  }

  async function submit(e: FormEvent) {
    e.preventDefault(); if (!selectedSchool) return;
    setSaving(true); setError(null); setNotice('');
    try {
      await api.post('/api/v1/calendar-events', {
        ...form,
        source_url: form.source_url || null,
        notes: form.notes || null,
        is_instructional: ['public_holiday', 'school_holiday', 'school_closure'].includes(form.event_type) ? false : form.is_instructional,
      }, { school_id: selectedSchool.id });
      setForm(blank); setShowForm(false); setNotice('Calendar event saved as pending approval.'); await load();
    } catch (e) { setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not save event'); }
    finally { setSaving(false); }
  }

  async function approve(event: CalendarEvent) {
    try { await api.patch('/api/v1/calendar-events/' + event.id, { is_approved: !event.is_approved }); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not update approval status'); }
  }
  async function remove(event: CalendarEvent) {
    if (!window.confirm('Delete calendar event "' + event.title + '"?')) return;
    try { await api.delete('/api/v1/calendar-events/' + event.id); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not delete event'); }
  }

  if (!selectedSchool) return <div><PageHeader title="School Calendar" /><Card className="p-6">Select a school from the header first.</Card></div>;
  return <div className="space-y-5">
    <PageHeader title="School Calendar" subtitle={`Terms, holidays, examinations, and school events for ${selectedSchool.name}`} actions={<Button onClick={() => setShowForm((v) => !v)}>{showForm ? 'Cancel' : '+ Add calendar event'}</Button>} />
    {error && <ErrorBanner message={error} onRetry={load} />}
    {notice && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    {showForm && <Card className="p-5"><form onSubmit={submit} className="space-y-4">
      <h2 className="font-semibold text-slate-900">New calendar event</h2>
      <p className="text-sm text-slate-600">Government dates must include a source URL and should be checked before approval. Events are school-scoped and are not automatically copied to other schools.</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">Event title<input required maxLength={200} value={form.title} onChange={(e) => change('title', e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label className="text-sm font-medium text-slate-700">Event type<select value={form.event_type} onChange={(e) => change('event_type', e.target.value as EventType)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2">{eventTypes.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}</select></label>
        <label className="text-sm font-medium text-slate-700">Start date<input required type="date" value={form.start_date} onChange={(e) => change('start_date', e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label className="text-sm font-medium text-slate-700">End date<input required type="date" min={form.start_date || undefined} value={form.end_date} onChange={(e) => change('end_date', e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label className="text-sm font-medium text-slate-700">Source<select value={form.source} onChange={(e) => change('source', e.target.value as EventSource)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2"><option value="school">School-created</option><option value="government">Government source</option><option value="exam_board">Examination authority</option><option value="other">Other</option></select></label>
        <label className="text-sm font-medium text-slate-700">Official source URL<input type="url" value={form.source_url} onChange={(e) => change('source_url', e.target.value)} placeholder="https://..." className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2" /></label>
      </div>
      {!['public_holiday','school_holiday','school_closure'].includes(form.event_type) && <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={form.is_instructional} onChange={(e) => change('is_instructional', e.target.checked)} /> School is open for instruction during this event</label>}
      <label className="block text-sm font-medium text-slate-700">Notes<textarea rows={2} value={form.notes} onChange={(e) => change('notes', e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2" /></label>
      <div className="flex justify-end"><Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save event for review'}</Button></div>
    </form></Card>}
    {loading ? <Spinner /> : events.length === 0 ? <Card className="p-8 text-center"><h2 className="font-semibold text-slate-900">No calendar events yet</h2><p className="mt-2 text-sm text-slate-600">Add terms, public holidays, school closures, and examination periods to establish the school calendar.</p></Card> : <Card className="divide-y divide-slate-200">{events.map((event) => <div key={event.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold text-slate-900">{event.title}</h3><span className={`rounded-full px-2 py-0.5 text-xs ${event.is_approved ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>{event.is_approved ? 'Approved' : 'Pending review'}</span></div><p className="mt-1 text-sm text-slate-600">{event.start_date === event.end_date ? event.start_date : event.start_date + ' – ' + event.end_date} · {event.event_type.replaceAll('_', ' ')} · {event.source.replaceAll('_', ' ')}</p><p className="mt-1 text-xs text-slate-500">{event.is_instructional ? 'Instructional day(s)' : 'Non-instructional'}</p>{event.source_url && <a href={event.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-indigo-700 underline">View source</a>}{event.notes && <p className="mt-2 text-sm text-slate-600">{event.notes}</p>}</div><div className="flex shrink-0 gap-2"><Button variant="secondary" onClick={() => void approve(event)}>{event.is_approved ? 'Unapprove' : 'Approve'}</Button><Button variant="danger" onClick={() => void remove(event)}>Delete</Button></div></div>)}</Card>}
    <Card className="p-4"><p className="text-sm text-slate-600">Calendar safety: events do not automatically mark attendance or close registers yet. Attendance will consume only approved events after its rules are implemented. Public holiday dates must be verified against the official government calendar for the selected country and year.</p></Card>
  </div>;
}
