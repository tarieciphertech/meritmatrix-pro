import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import { useSchool } from '../lib/school-context';
import { Button, Card, EmptyState, ErrorBanner, PageHeader, Select, Spinner, Table, Td } from '../components/ui';

type AuditEvent = {
  id: string;
  school_id: string | null;
  actor_user_id: string | null;
  actor_name: string;
  actor_identifier: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown>;
  created_at: string | null;
};

const PAGE_SIZE = 50;
const ACTIONS = [
  'attendance.register_saved',
  'assessment.created',
  'assessment.updated',
  'assessment.results_published',
  'assessment.results_unpublished',
  'assessment.marks_saved',
  'assessment.marks_submitted_for_review',
  'assessment.marks_returned_to_draft',
  'grading_scale.replaced',
  'fees.charge_created',
  'fees.payment_recorded',
  'student.created',
  'student.updated',
  'student.archived',
  'staff.created',
  'staff.updated',
  'staff.archived',
  'staff.account_provisioned',
  'enrollment.created',
  'enrollment.updated',
  'enrollment.completed',
  'enrollment.withdrawn',
  'enrollment.cancelled',
  'teaching_assignment.created',
  'teaching_assignment.updated',
  'teaching_assignment.deactivated',
];

function readable(value: string) {
  return value.replaceAll('_', ' ').replaceAll('.', ' · ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function AuditLogsPage() {
  const { selectedSchool } = useSchool();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [action, setAction] = useState('');
  const [entityType, setEntityType] = useState('');
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const activeSchoolIdRef = useRef<string | null>(selectedSchool?.id ?? null);
  activeSchoolIdRef.current = selectedSchool?.id ?? null;

  useEffect(() => {
    requestIdRef.current += 1;
    setEvents([]);
    setError(null);
    setOffset(0);
    setLoading(false);
  }, [selectedSchool?.id]);

  const loadEvents = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    if (!selectedSchool) { setEvents([]); setLoading(false); return; }
    const requestSchoolId = selectedSchool.id;
    setLoading(true);
    setError(null);
    try {
      const rows = await api.get<AuditEvent[]>('/api/v1/audit-logs', {
        school_id: requestSchoolId,
        limit: PAGE_SIZE,
        offset,
        ...(action ? { action } : {}),
        ...(entityType ? { entity_type: entityType } : {}),
      });
      if (requestIdRef.current !== requestId || activeSchoolIdRef.current !== requestSchoolId) return;
      setEvents(rows);
    } catch (err) {
      if (requestIdRef.current !== requestId || activeSchoolIdRef.current !== requestSchoolId) return;
      setEvents([]);
      setError(err instanceof Error ? err.message : 'Could not load audit history.');
    } finally {
      if (requestIdRef.current === requestId && activeSchoolIdRef.current === requestSchoolId) setLoading(false);
    }
  }, [selectedSchool, action, entityType, offset]);

  useEffect(() => { void loadEvents(); }, [loadEvents]);

  function changeAction(value: string) { setAction(value); setOffset(0); }
  function changeEntityType(value: string) { setEntityType(value); setOffset(0); }

  if (!selectedSchool) return <div><PageHeader title="Audit History" subtitle="Review administrative activity for a selected school."/><Card className="p-6">Choose a school from the selector above.</Card></div>;

  return <div className="space-y-5">
    <PageHeader title="Audit History" subtitle={'Administrative activity recorded for ' + selectedSchool.name + '.'} actions={<Button variant="secondary" onClick={() => void loadEvents()} disabled={loading}>Refresh</Button>} />
    {error && <ErrorBanner message={error} onRetry={() => void loadEvents()} />}
    <Card className="p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">Action
          <Select className="mt-1" value={action} onChange={e => changeAction(e.target.value)}>
            <option value="">All actions</option>
            {ACTIONS.map(item => <option key={item} value={item}>{readable(item)}</option>)}
          </Select>
        </label>
        <label className="text-sm font-medium text-slate-700">Record type
          <Select className="mt-1" value={entityType} onChange={e => changeEntityType(e.target.value)}>
            <option value="">All record types</option>
            {['attendance_register', 'assessment', 'grading_scale', 'fee_charge', 'fee_payment', 'student', 'staff', 'enrollment', 'teaching_assignment'].map(item => <option key={item} value={item}>{readable(item)}</option>)}
          </Select>
        </label>
      </div>
    </Card>
    <Card className="p-0">
      {loading ? <Spinner label="Loading audit history…" /> : events.length === 0 ? <EmptyState title="No audit events found" hint="Activity appears here when supported student, staff, enrollment, teaching assignment, attendance, assessment, grading, or fee operations are performed." /> : (
        <Table headers={['Date and time', 'Action', 'Record', 'Actor', 'Details']}>
          {events.map(event => <tr key={event.id}>
            <Td className="min-w-44">{event.created_at ? new Date(event.created_at).toLocaleString() : '—'}</Td>
            <Td><span className="font-medium text-slate-900">{readable(event.action)}</span></Td>
            <Td><p className="font-medium text-slate-800">{readable(event.entity_type)}</p><p className="text-xs text-slate-500">{event.entity_id ?? '—'}</p></Td>
            <Td><p className="font-medium text-slate-800">{event.actor_name}</p><p className="text-xs text-slate-500">{event.actor_identifier ?? event.actor_user_id ?? ''}</p></Td>
            <Td><pre className="max-w-md whitespace-pre-wrap break-words text-xs text-slate-600">{JSON.stringify(event.details, null, 2)}</pre></Td>
          </tr>)}
        </Table>
      )}
      <div className="flex items-center justify-between border-t border-slate-100 p-3">
        <p className="text-xs text-slate-500">Showing up to {PAGE_SIZE} events per page.</p>
        <div className="flex gap-2">
          <Button variant="secondary" disabled={loading || offset === 0} onClick={() => setOffset(value => Math.max(0, value - PAGE_SIZE))}>Previous</Button>
          <Button variant="secondary" disabled={loading || events.length < PAGE_SIZE} onClick={() => setOffset(value => value + PAGE_SIZE)}>Next</Button>
        </div>
      </div>
    </Card>
  </div>;
}
