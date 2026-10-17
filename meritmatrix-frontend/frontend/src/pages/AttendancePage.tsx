import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { ClassResponse } from '../types';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

type AttendanceRow = {
 id: string; enrollment_id: string; student_id: string; student_number: string;
 student_name: string; class_id: string; class_name: string; class_code: string;
 status: 'unmarked'|'present'|'absent'|'late'|'excused'|'sick'|'left_early'; notes?: string|null;
};
type Status = AttendanceRow['status'];
const statuses: {value:Status;label:string}[] = [
 {value:'unmarked',label:'Not marked'}, {value:'present',label:'Present'}, {value:'absent',label:'Absent'},
 {value:'late',label:'Late'}, {value:'excused',label:'Excused'}, {value:'sick',label:'Sick'}, {value:'left_early',label:'Left early'},
];
function localToday() { const d = new Date(); return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-'); }

export default function AttendancePage() {
 const {selectedSchool}=useSchool();
 const [classes,setClasses]=useState<ClassResponse[]>([]);
 const [classId,setClassId]=useState('');
 const [day,setDay]=useState(localToday());
 const [session,setSession]=useState('full_day');
 const [rows,setRows]=useState<AttendanceRow[]>([]);
 const [loading,setLoading]=useState(false);
 const [saving,setSaving]=useState(false);
 const [error,setError]=useState<string|null>(null);
 const [notice,setNotice]=useState('');
 const loadClasses=useCallback(async()=>{if(!selectedSchool){setClasses([]);setClassId('');return;}try{const list=await api.get<ClassResponse[]>('/api/v1/classes',{school_id:selectedSchool.id});const active=list.filter(x=>x.is_active);setClasses(active);setClassId(prev=>active.some(x=>x.id===prev)?prev:active[0]?.id??'');}catch(e){setError(e instanceof Error?e.message:'Could not load classes');}},[selectedSchool]);
 useEffect(()=>{void loadClasses();},[loadClasses]);
 const loadRoster=useCallback(async()=>{if(!selectedSchool||!classId||!day){setRows([]);return;}setLoading(true);setError(null);setNotice('');try{const list=await api.get<AttendanceRow[]>('/api/v1/attendance/roster',{school_id:selectedSchool.id,class_id:classId,attendance_date:day,session});setRows(list);}catch(e){setRows([]);setError(e instanceof ApiError?e.message:e instanceof Error?e.message:'Could not load the class register');}finally{setLoading(false);}},[selectedSchool,classId,day,session]);
 useEffect(()=>{void loadRoster();},[loadRoster]);
 function mark(enrollmentId:string,status:Status){setRows(prev=>prev.map(row=>row.enrollment_id===enrollmentId?{...row,status}:row));}
 function note(enrollmentId:string,notes:string){setRows(prev=>prev.map(row=>row.enrollment_id===enrollmentId?{...row,notes}:row));}
 async function save(){if(!selectedSchool||!classId)return;const entries=rows.filter(row=>row.status!=='unmarked').map(row=>({enrollment_id:row.enrollment_id,status:row.status,notes:row.notes||null}));if(!entries.length){setError('Mark at least one student before saving.');return;}setSaving(true);setError(null);setNotice('');try{await api.put<AttendanceRow[]>('/api/v1/attendance/register',{attendance_date:day,session,entries},{school_id:selectedSchool.id,class_id:classId});setNotice(`Saved attendance for ${entries.length} student(s).`);await loadRoster();}catch(e){setError(e instanceof ApiError?e.message:e instanceof Error?e.message:'Could not save attendance');}finally{setSaving(false);}}
 if(!selectedSchool)return <div><PageHeader title="Daily Attendance"/><Card className="p-6">Select a school first.</Card></div>;
 const marked=rows.filter(r=>r.status!=='unmarked').length;
 return <div className="space-y-5"><PageHeader title="Daily Attendance" subtitle={`Take and review the class register at ${selectedSchool.name}`} actions={<Button onClick={()=>void loadRoster()} disabled={loading||!classId}>Refresh register</Button>}/>
 {error&&<ErrorBanner message={error} onRetry={()=>void loadRoster()}/>}
 {notice&&<div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
 <Card className="p-4"><div className="grid gap-3 sm:grid-cols-3">
 <label className="text-sm font-medium text-slate-700">Class<select value={classId} onChange={e=>setClassId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2" required><option value="">Choose class…</option>{classes.map(c=><option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}</select></label>
 <label className="text-sm font-medium text-slate-700">Attendance date<input type="date" value={day} onChange={e=>setDay(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2" required/></label>
 <label className="text-sm font-medium text-slate-700">Session<select value={session} onChange={e=>setSession(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="full_day">Full day</option><option value="morning">Morning</option><option value="afternoon">Afternoon</option><option value="period_1">Period 1</option><option value="period_2">Period 2</option><option value="period_3">Period 3</option></select></label>
 </div><div className="mt-3 text-sm text-slate-500">{rows.length} enrolled student(s) · {marked} marked</div></Card>
 {loading?<Card className="p-8"><Spinner label="Loading register…"/></Card>:rows.length===0?<Card className="p-8 text-center text-sm text-slate-500">{error?'The register could not be loaded. Resolve the error above, then refresh the register.':'No active enrollments found for this class and date. Check the academic year and enrollment setup.'}</Card>:<Card className="overflow-hidden"><div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-sm"><thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left font-semibold text-slate-600">Student</th><th className="px-4 py-3 text-left font-semibold text-slate-600">Attendance</th><th className="px-4 py-3 text-left font-semibold text-slate-600">Notes</th></tr></thead><tbody className="divide-y divide-slate-100 bg-white">{rows.map(row=><tr key={row.enrollment_id}><td className="whitespace-nowrap px-4 py-3"><div className="font-medium text-slate-900">{row.student_name}</div><div className="text-xs text-slate-500">{row.student_number}</div></td><td className="px-4 py-3"><select aria-label={`Attendance for ${row.student_name}`} value={row.status} onChange={e=>mark(row.enrollment_id,e.target.value as Status)} className="rounded-md border border-slate-300 bg-white p-2">{statuses.map(s=><option key={s.value} value={s.value}>{s.label}</option>)}</select></td><td className="px-4 py-3"><input aria-label={`Notes for ${row.student_name}`} value={row.notes??''} onChange={e=>note(row.enrollment_id,e.target.value)} placeholder="Optional note" className="w-full min-w-40 rounded-md border border-slate-300 p-2"/></td></tr>)}</tbody></table></div><div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 p-4"><p className="text-xs text-slate-500">Only marked students will be saved. Re-saving updates the existing mark for this date and session.</p><Button onClick={()=>void save()} disabled={saving||marked===0}>{saving?'Saving…':`Save register (${marked})`}</Button></div></Card>}
 </div>;
}
