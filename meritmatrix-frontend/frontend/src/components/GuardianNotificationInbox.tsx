import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import { Button, Card, EmptyState, ErrorBanner, Spinner } from './ui';

type NotificationItem = {
  id: string;
  school_id: string | null;
  student_id: string | null;
  notification_type: string;
  title: string;
  message: string;
  data: Record<string, unknown>;
  read_at: string | null;
  created_at: string | null;
};

export default function GuardianNotificationInbox({ schoolId }: { schoolId: string }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const activeSchoolIdRef = useRef(schoolId);
  activeSchoolIdRef.current = schoolId;

  useEffect(() => {
    requestIdRef.current += 1;
    setItems([]);
    setError(null);
    setLoading(false);
    setSaving(false);
  }, [schoolId]);

  const load = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    if (!schoolId) { setItems([]); setLoading(false); return; }
    const requestSchoolId = schoolId;
    setLoading(true);
    setError(null);
    try {
      const rows = await api.get<NotificationItem[]>('/api/v1/notifications', { school_id: requestSchoolId, limit: 20 });
      if (requestIdRef.current !== requestId || activeSchoolIdRef.current !== requestSchoolId) return;
      setItems(rows);
    } catch (err) {
      if (requestIdRef.current !== requestId || activeSchoolIdRef.current !== requestSchoolId) return;
      setItems([]);
      setError(err instanceof Error ? err.message : 'Could not load notifications.');
    } finally {
      if (requestIdRef.current === requestId && activeSchoolIdRef.current === requestSchoolId) setLoading(false);
    }
  }, [schoolId]);

  useEffect(() => { void load(); }, [load]);

  async function markRead(item: NotificationItem) {
    if (item.read_at || !schoolId || item.school_id !== schoolId) return;
    const requestSchoolId = schoolId;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.post<NotificationItem>('/api/v1/notifications/' + item.id + '/read', {});
      if (activeSchoolIdRef.current !== requestSchoolId) return;
      setItems(current => current.map(row => row.id === updated.id ? updated : row));
    } catch (err) {
      if (activeSchoolIdRef.current !== requestSchoolId) return;
      setError(err instanceof Error ? err.message : 'Could not mark notification as read.');
    } finally {
      if (activeSchoolIdRef.current === requestSchoolId) setSaving(false);
    }
  }

  async function markAllRead() {
    if (!schoolId) return;
    const requestSchoolId = schoolId;
    setSaving(true);
    setError(null);
    try {
      await api.post<{ marked_read: number }>('/api/v1/notifications/read-all', undefined, { school_id: requestSchoolId });
      if (activeSchoolIdRef.current !== requestSchoolId) return;
      await load();
    } catch (err) {
      if (activeSchoolIdRef.current !== requestSchoolId) return;
      setError(err instanceof Error ? err.message : 'Could not mark notifications as read.');
    } finally {
      if (activeSchoolIdRef.current === requestSchoolId) setSaving(false);
    }
  }

  const unreadCount = items.filter(item => !item.read_at).length;

  return <Card className="p-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="font-semibold text-slate-900">School notifications</h2><p className="mt-1 text-sm text-slate-500">{unreadCount} unread notification{unreadCount === 1 ? '' : 's'} for this school.</p></div>
      <div className="flex gap-2"><Button variant="secondary" onClick={() => void load()} disabled={loading || saving}>Refresh</Button><Button variant="secondary" onClick={() => void markAllRead()} disabled={loading || saving || unreadCount === 0}>Mark all read</Button></div>
    </div>
    {error && <div className="mt-3"><ErrorBanner message={error} onRetry={() => void load()} /></div>}
    {loading ? <Spinner label="Loading notifications…" /> : items.length === 0 ? <EmptyState title="You're all caught up" hint="Important attendance, results, and fee updates from the school will appear here." /> : (
      <ul className="mt-4 divide-y divide-slate-100">
        {items.map(item => <li key={item.id} className={'flex flex-col gap-3 py-3 sm:flex-row sm:items-start sm:justify-between ' + (!item.read_at ? 'bg-indigo-50/50 px-3' : '')}>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2"><p className="font-medium text-slate-900">{item.title}</p>{!item.read_at && <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">New</span>}</div>
            <p className="mt-1 text-sm text-slate-600">{item.message}</p>
            <p className="mt-1 text-xs text-slate-400">{item.created_at ? new Date(item.created_at).toLocaleString() : ''}</p>
          </div>
          {!item.read_at && <Button variant="secondary" className="shrink-0 self-start" disabled={saving} onClick={() => void markRead(item)}>Mark read</Button>}
        </li>)}
      </ul>
    )}
  </Card>;
}
