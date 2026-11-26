import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';

type NotificationItem = {
  id: string;
  school_id: string | null;
  notification_type: string;
  title: string;
  message: string;
  read_at: string | null;
  created_at: string | null;
};

export default function NotificationCenter({ schoolId }: { schoolId?: string }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const activeSchoolIdRef = useRef(schoolId);
  activeSchoolIdRef.current = schoolId;

  const load = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    const requestSchoolId = schoolId;
    setLoading(true);
    setError(null);
    try {
      const rows = await api.get<NotificationItem[]>('/api/v1/notifications', {
        school_id: schoolId,
        limit: 20,
      });
      if (requestIdRef.current === requestId && activeSchoolIdRef.current === requestSchoolId) setItems(rows);
    } catch (err) {
      if (requestIdRef.current === requestId && activeSchoolIdRef.current === requestSchoolId) setError(err instanceof Error ? err.message : 'Could not load notifications.');
    } finally {
      if (requestIdRef.current === requestId && activeSchoolIdRef.current === requestSchoolId) setLoading(false);
    }
  }, [schoolId]);

  useEffect(() => {
    requestIdRef.current += 1;
    setItems([]);
    setError(null);
    setLoading(false);
  }, [schoolId]);

  useEffect(() => { void load(); }, [load]);

  async function markRead(item: NotificationItem) {
    if (item.read_at || savingId) return;
    const requestSchoolId = schoolId;
    setSavingId(item.id);
    setError(null);
    try {
      const updated = await api.post<NotificationItem>(`/api/v1/notifications/${item.id}/read`, {});
      if (activeSchoolIdRef.current === requestSchoolId) setItems(current => current.map(row => row.id === updated.id ? updated : row));
    } catch (err) {
      if (activeSchoolIdRef.current === requestSchoolId) setError(err instanceof Error ? err.message : 'Could not mark notification as read.');
    } finally {
      if (activeSchoolIdRef.current === requestSchoolId) setSavingId(null);
    }
  }

  async function markAllRead() {
    if (savingId) return;
    const requestSchoolId = schoolId;
    setSavingId('all');
    setError(null);
    try {
      await api.post<{ marked_read: number }>('/api/v1/notifications/read-all', undefined, {
        school_id: schoolId,
      });
      if (activeSchoolIdRef.current === requestSchoolId) await load();
    } catch (err) {
      if (activeSchoolIdRef.current === requestSchoolId) setError(err instanceof Error ? err.message : 'Could not mark notifications as read.');
    } finally {
      if (activeSchoolIdRef.current === requestSchoolId) setSavingId(null);
    }
  }

  const unread = items.filter(item => !item.read_at).length;

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={unread ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-expanded={open}
        onClick={() => { setOpen(value => !value); if (!open) void load(); }}
        className="relative rounded-md p-2 text-slate-600 transition-colors hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
          <path d="M10 21h4" />
        </svg>
        {unread > 0 && <span className="absolute -right-0.5 -top-0.5 min-w-4 rounded-full bg-rose-600 px-1 text-center text-[10px] font-bold leading-4 text-white">{unread > 99 ? '99+' : unread}</span>}
      </button>

      {open && (
        <>
          <button type="button" aria-label="Close notifications" className="fixed inset-0 z-30 cursor-default" onClick={() => setOpen(false)} />
          <section aria-label="Notifications" className="absolute right-0 z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
              <div><h2 className="text-sm font-semibold text-slate-900">Notifications</h2><p className="text-xs text-slate-500">{unread} unread</p></div>
              <div className="flex gap-2">
                <button type="button" onClick={() => void load()} disabled={loading || Boolean(savingId)} className="text-xs font-medium text-slate-600 hover:text-indigo-700 disabled:opacity-50">Refresh</button>
                <button type="button" onClick={() => void markAllRead()} disabled={loading || Boolean(savingId) || unread === 0} className="text-xs font-medium text-indigo-700 hover:text-indigo-900 disabled:opacity-50">Mark all read</button>
              </div>
            </div>
            {error && <p role="alert" className="px-4 py-2 text-xs text-rose-700">{error}</p>}
            <div className="max-h-[min(65vh,28rem)] overflow-y-auto">
              {loading && items.length === 0 ? <p className="p-5 text-sm text-slate-500">Loading notifications…</p> :
                items.length === 0 ? <div className="p-6 text-center"><p className="text-sm font-medium text-slate-800">You're all caught up</p><p className="mt-1 text-xs text-slate-500">Important updates will appear here.</p></div> :
                <ul className="divide-y divide-slate-100">
                  {items.map(item => (
                    <li key={item.id} className={`px-4 py-3 ${item.read_at ? '' : 'bg-indigo-50/60'}`}>
                      <div className="flex items-start gap-3">
                        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${item.read_at ? 'bg-slate-200' : 'bg-indigo-600'}`} />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-slate-900">{item.title}</p>
                          <p className="mt-1 text-xs leading-5 text-slate-600">{item.message}</p>
                          <div className="mt-2 flex items-center justify-between gap-2">
                            <time className="text-[11px] text-slate-400">{item.created_at ? new Date(item.created_at).toLocaleString() : ''}</time>
                            {!item.read_at && <button type="button" onClick={() => void markRead(item)} disabled={Boolean(savingId)} className="text-xs font-semibold text-indigo-700 hover:underline disabled:opacity-50">Mark read</button>}
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              }
            </div>
          </section>
        </>
      )}
    </div>
  );
}
