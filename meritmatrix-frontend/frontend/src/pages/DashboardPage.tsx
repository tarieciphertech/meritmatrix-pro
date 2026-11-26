import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import { useSchool } from '../lib/school-context';
import type { EnrollmentResponse, GuardianResponse, StaffResponse, StudentResponse } from '../types';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

interface Counts { students: number | null; guardians: number | null; staff: number | null; enrollments: number | null; }
const MAX_COUNT_FETCH = 200;
type Assignment = { id: string; class_name: string; class_code: string; subject_name: string; subject_code: string; start_date: string; end_date?: string | null };
type Slot = { id: string; weekday: number; start_time: string; end_time: string; room?: string | null; class_name: string; subject_name: string };
type Assessment = { id: string; title: string; assessment_date?: string | null; class_name: string; subject_name: string; marks_submitted: boolean; is_published: boolean };
type CalendarEvent = { id: string; title: string; event_type: string; start_date: string; end_date: string; is_approved: boolean };
type Notification = { id: string; title: string; message: string; created_at: string; read_at?: string | null };
type AttendanceRow = { enrollment_id: string; status: string; student_name: string; class_name: string };
const today = () => { const d = new Date(); return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-'); };
const dayIndex = () => (new Date().getDay() + 6) % 7;

function TeacherDashboard({ schoolId }: { schoolId: string }) {
  const [assignments,setAssignments]=useState<Assignment[]>([]);
  const [slots,setSlots]=useState<Slot[]>([]);
  const [assessments,setAssessments]=useState<Assessment[]>([]);
  const [events,setEvents]=useState<CalendarEvent[]>([]);
  const [notifications,setNotifications]=useState<Notification[]>([]);
  const [attendance,setAttendance]=useState<AttendanceRow[]>([]);
  const [studentCount,setStudentCount]=useState<number|null>(null);
  const [enrollmentCount,setEnrollmentCount]=useState<number|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);
  const requestRef=useRef(0);
  const load=useCallback(async()=>{
    const request=++requestRef.current; setLoading(true); setError(null);
    const date=today();
    const results=await Promise.allSettled([
      api.get<Assignment[]>('/api/v1/teaching-assignments',{school_id:schoolId,active_only:true}),
      api.get<Slot[]>('/api/v1/timetable',{school_id:schoolId,active_on:date}),
      api.get<Assessment[]>('/api/v1/assessments',{school_id:schoolId,include_unpublished:true}),
      api.get<CalendarEvent[]>('/api/v1/calendar-events',{school_id:schoolId,from_date:date,approved_only:true}),
      api.get<Notification[]>('/api/v1/notifications',{school_id:schoolId,limit:100}),
      api.get<AttendanceRow[]>('/api/v1/attendance',{school_id:schoolId,attendance_date:date}),
      api.get<StudentResponse[]>('/api/v1/students',{school_id:schoolId,limit:200}),
      api.get<EnrollmentResponse[]>('/api/v1/enrollments',{school_id:schoolId,limit:200}),
    ]);
    if(requestRef.current!==request)return;
    const [a,t,as,c,n,at,students,enrollments]=results;
    setAssignments(a.status==='fulfilled'?a.value:[]);
    setSlots(t.status==='fulfilled'?t.value:[]);
    setAssessments(as.status==='fulfilled'?as.value:[]);
    setEvents(c.status==='fulfilled'?c.value:[]);
    setNotifications(n.status==='fulfilled'?n.value:[]);
    setAttendance(at.status==='fulfilled'?at.value:[]);
    setStudentCount(students.status==='fulfilled'?students.value.length:null);
    setEnrollmentCount(enrollments.status==='fulfilled'?enrollments.value.length:null);
    const failures=results.filter(r=>r.status==='rejected');
    if(failures.length===results.length)setError('Teacher workspace data could not be loaded. Check your connection and access, then retry.');
    else if(failures.length)setError('Some teacher workspace sections could not be loaded. Available sections are shown; retry to refresh.');
    setLoading(false);
  },[schoolId]);
  useEffect(()=>{void load();return()=>{requestRef.current+=1;};},[load]);
  const activeAssignments=assignments.filter(a=>a.start_date<=today()&&(!a.end_date||a.end_date>=today()));
  const todaySlots=slots.filter(s=>s.weekday===dayIndex()).sort((a,b)=>a.start_time.localeCompare(b.start_time));
  const attendanceCaptured=attendance.length;
  const absentOrLate=attendance.filter(r=>r.status==='absent'||r.status==='late').length;
  const upcoming=assessments.filter(a=>a.assessment_date&&a.assessment_date>=today()&&!a.is_published).sort((a,b)=>(a.assessment_date||'').localeCompare(b.assessment_date||'')).slice(0,5);
  const draftAssessments=assessments.filter(a=>!a.is_published&&!a.marks_submitted).length;
  const unread=notifications.filter(n=>!n.read_at).length;
  const fmt=(date:string)=>new Date(date+'T00:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric'});
  if(loading)return <Spinner label="Loading your teaching workspace…"/>;
  return <div className="space-y-5">
    {error&&<ErrorBanner message={error} onRetry={load}/>}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {[{label:'My classes & subjects',value:activeAssignments.length,detail:'Current active teaching assignments',to:'/timetable'},{label:'Assigned students',value:studentCount===null?'—':studentCount===200?'200+':studentCount,detail:studentCount===200?'At least 200 · list limit reached':'Students in your permitted classes',to:'/students'},{label:'Active enrollments',value:enrollmentCount===null?'—':enrollmentCount===200?'200+':enrollmentCount,detail:enrollmentCount===200?'At least 200 · list limit reached':'Enrollment records in your scope',to:'/students'},{label:"Today's lessons",value:todaySlots.length,detail:'From your school timetable',to:'/timetable'},{label:'Attendance records today',value:attendanceCaptured,detail:'Saved records in your assigned classes',to:'/attendance'},{label:'Draft assessments',value:draftAssessments,detail:'Not yet submitted for review',to:'/assessments'}].map(item=><Link key={item.label} to={item.to}><Card className="h-full p-5 transition-all hover:-translate-y-0.5 hover:shadow-md"><p className="text-sm font-medium text-slate-500">{item.label}</p><p className="mt-2 text-3xl font-semibold text-slate-900">{item.value}</p><p className="mt-1 text-xs text-slate-500">{item.detail}</p></Card></Link>)}
    </div>
    <div className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
      <Card className="overflow-hidden"><div className="flex items-center justify-between border-b border-slate-100 p-4"><div><h2 className="font-semibold text-slate-900">Today's teaching schedule</h2><p className="text-xs text-slate-500">{new Date().toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'})}</p></div><Link className="text-sm font-medium text-indigo-700 hover:underline" to="/timetable">Full timetable →</Link></div>
        {todaySlots.length? <div className="divide-y divide-slate-100">{todaySlots.map(slot=><div key={slot.id} className="flex gap-4 p-4"><div className="w-24 shrink-0 text-sm font-semibold tabular-nums text-indigo-700">{slot.start_time.slice(0,5)}–{slot.end_time.slice(0,5)}</div><div><p className="font-semibold text-slate-900">{slot.subject_name} · {slot.class_name}</p>{slot.room&&<p className="text-sm text-slate-500">{slot.room}</p>}</div></div>)}</div>:<div className="p-6 text-sm text-slate-600">No lessons are scheduled for today. If this is unexpected, ask your school administrator to publish your timetable.</div>}
      </Card>
      <Card className="p-4"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900">My teaching assignments</h2><Link className="text-sm text-indigo-700 hover:underline" to="/timetable">Timetable</Link></div>{activeAssignments.length?<div className="mt-3 space-y-3">{activeAssignments.slice(0,6).map(a=><div key={a.id} className="border-b border-slate-100 pb-3 last:border-0"><p className="font-medium text-slate-800">{a.class_name} · {a.subject_name}</p><p className="text-xs text-slate-500">From {fmt(a.start_date)}{a.end_date?' to '+fmt(a.end_date):' · ongoing'}</p></div>)}</div>:<p className="mt-3 text-sm text-slate-600">No current class-subject assignments are linked to your account.</p>}</Card>
    </div>
    <div className="grid gap-5 lg:grid-cols-2">
      <Card className="p-4"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900">Attendance overview</h2><Link to="/attendance" className="text-sm text-indigo-700 hover:underline">Open register</Link></div><p className="mt-2 text-2xl font-semibold text-slate-900">{attendanceCaptured}</p><p className="text-sm text-slate-500">Saved attendance records in your assigned classes today</p>{attendanceCaptured>0&&<p className="mt-3 text-xs text-slate-500">{absentOrLate} absent or late record(s) may need follow-up.</p>}</Card>
      <Card className="p-4"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900">Assessments & marking</h2><Link to="/assessments" className="text-sm text-indigo-700 hover:underline">Open assessments</Link></div>{upcoming.length?<div className="mt-3 space-y-3">{upcoming.map(a=><div key={a.id} className="flex justify-between gap-3 border-b border-slate-100 pb-2 last:border-0"><div><p className="font-medium text-slate-800">{a.title}</p><p className="text-xs text-slate-500">{a.class_name} · {a.subject_name}</p></div><span className="shrink-0 text-sm text-slate-600">{fmt(a.assessment_date!)}</span></div>)}</div>:<p className="mt-3 text-sm text-slate-600">No upcoming unpublished assessments are scheduled.</p>}<p className="mt-3 text-xs text-slate-500">{draftAssessments} draft assessment(s) not yet submitted for review.</p></Card>
      <Card className="p-4"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900">School calendar</h2><Link to="/school-calendar" className="text-sm text-indigo-700 hover:underline">View calendar</Link></div>{events.length?<div className="mt-3 space-y-2">{events.slice(0,5).map(e=><div key={e.id} className="flex justify-between gap-3"><span className="text-sm text-slate-800">{e.title}</span><span className="shrink-0 text-xs text-slate-500">{fmt(e.start_date)}</span></div>)}</div>:<p className="mt-3 text-sm text-slate-600">No approved school events are coming up from today.</p>}</Card>
      <Card className="p-4"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900">Notifications</h2><span className="rounded-full bg-indigo-50 px-2 py-1 text-xs font-semibold text-indigo-700">{unread} unread · latest 100</span></div>{notifications.length?<div className="mt-3 space-y-3">{notifications.slice(0,5).map(n=><div key={n.id} className="border-b border-slate-100 pb-2 last:border-0"><p className="text-sm font-medium text-slate-800">{n.title}</p><p className="text-xs text-slate-500">{n.message}</p></div>)}</div>:<p className="mt-3 text-sm text-slate-600">You have no notifications for this school.</p>}</Card>
    </div>
  </div>;
}


function AdminSchoolOverview({ schoolId }: { schoolId: string }) {
  const [attendance, setAttendance] = useState<AttendanceRow[]>([]);
  const [pendingReviews, setPendingReviews] = useState<Assessment[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [unreadCount, setUnreadCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const date = today();
    setLoading(true);
    setError(null);
    void Promise.allSettled([
      api.get<AttendanceRow[]>('/api/v1/attendance', { school_id: schoolId, attendance_date: date }),
      api.get<Assessment[]>('/api/v1/assessments', { school_id: schoolId, include_unpublished: true }),
      api.get<CalendarEvent[]>('/api/v1/calendar-events', { school_id: schoolId, from_date: date, approved_only: true }),
      api.get<Notification[]>('/api/v1/notifications', { school_id: schoolId, unread_only: true, limit: 100 }),
    ]).then(results => {
      if (cancelled) return;
      const [attendanceResult, assessmentResult, eventResult, notificationResult] = results;
      setAttendance(attendanceResult.status === 'fulfilled' ? attendanceResult.value : []);
      setPendingReviews(assessmentResult.status === 'fulfilled'
        ? assessmentResult.value.filter(item => item.marks_submitted && !item.is_published)
        : []);
      setEvents(eventResult.status === 'fulfilled' ? eventResult.value.slice(0, 4) : []);
      setUnreadCount(notificationResult.status === 'fulfilled' ? notificationResult.value.length : null);
      const failed = results.filter(result => result.status === 'rejected').length;
      if (failed === results.length) setError('School overview data could not be loaded. Check your access and retry.');
      else if (failed > 0) setError('Some overview figures are unavailable. The remaining sections are still shown.');
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [schoolId, refreshKey]);

  const attendanceExceptions = attendance.filter(row => ['absent', 'late', 'sick'].includes(row.status)).length;
  const fmt = (value: string) => new Date(value + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

  return <section className="mb-5 space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div><h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">School operations</h2><p className="mt-1 text-xs text-slate-400">Live activity and items requiring attention</p></div>
      <div className="flex items-center gap-3"><span className="text-xs text-slate-400">Today · {fmt(today())}</span><Button variant="secondary" className="!px-2 !py-1 text-xs" disabled={loading} onClick={() => setRefreshKey(value => value + 1)}>Refresh overview</Button></div>
    </div>
    {error && <ErrorBanner message={error} />}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Link to="/attendance"><Card className="h-full p-4 transition-shadow hover:shadow-md"><p className="text-sm font-medium text-slate-500">Attendance recorded today</p><p className="mt-2 text-3xl font-semibold text-slate-900">{loading ? '—' : attendance.length}</p><p className="mt-1 text-xs text-slate-500">{attendanceExceptions} absent, late or sick record(s)</p></Card></Link>
      <Link to="/assessments"><Card className="h-full p-4 transition-shadow hover:shadow-md"><p className="text-sm font-medium text-slate-500">Results awaiting review</p><p className="mt-2 text-3xl font-semibold text-slate-900">{loading ? '—' : pendingReviews.length}</p><p className="mt-1 text-xs text-slate-500">Submitted marks not yet published</p></Card></Link>
      <Link to="/school-calendar"><Card className="h-full p-4 transition-shadow hover:shadow-md"><p className="text-sm font-medium text-slate-500">Upcoming school events</p><p className="mt-2 text-3xl font-semibold text-slate-900">{loading ? '—' : events.length}</p><p className="mt-1 text-xs text-slate-500">Approved events from today onward</p></Card></Link>
      <Card className="p-4"><p className="text-sm font-medium text-slate-500">Unread notifications</p><p className="mt-2 text-3xl font-semibold text-slate-900">{loading || unreadCount === null ? '—' : unreadCount === 100 ? '100+' : unreadCount}</p><p className="mt-1 text-xs text-slate-500">Open the bell in the top bar to review</p></Card>
    </div>
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="p-4">
        <div className="flex items-center justify-between"><h3 className="font-semibold text-slate-900">Assessment review queue</h3><Link to="/assessments" className="text-sm font-medium text-indigo-700 hover:underline">Review assessments →</Link></div>
        {loading ? <p className="mt-3 text-sm text-slate-500">Loading review queue…</p> : pendingReviews.length ? <ul className="mt-3 divide-y divide-slate-100">{pendingReviews.slice(0, 4).map(item => <li key={item.id} className="py-2"><p className="text-sm font-medium text-slate-800">{item.title}</p><p className="text-xs text-slate-500">{item.class_name} · {item.subject_name}</p></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">No submitted assessments are waiting for review.</p>}
      </Card>
      <Card className="p-4">
        <div className="flex items-center justify-between"><h3 className="font-semibold text-slate-900">Upcoming school calendar</h3><Link to="/school-calendar" className="text-sm font-medium text-indigo-700 hover:underline">Open calendar →</Link></div>
        {loading ? <p className="mt-3 text-sm text-slate-500">Loading calendar…</p> : events.length ? <ul className="mt-3 divide-y divide-slate-100">{events.map(event => <li key={event.id} className="flex items-center justify-between gap-3 py-2"><div><p className="text-sm font-medium text-slate-800">{event.title}</p><p className="text-xs text-slate-500">{event.event_type.replaceAll('_', ' ')}</p></div><span className="shrink-0 text-xs text-slate-500">{fmt(event.start_date)}{event.end_date !== event.start_date ? `–${fmt(event.end_date)}` : ''}</span></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">No approved upcoming events are scheduled.</p>}
      </Card>
    </div>
    <div className="flex flex-wrap gap-2">
      <Link to="/students" className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">Manage students</Link>
      <Link to="/staff" className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Manage staff</Link>
      <Link to="/fees" className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Fees & payments</Link>
      <Link to="/report-cards" className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Report cards</Link>
    </div>
  </section>;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const isTeacher = (user?.roles ?? []).some((role) => role.name === 'TEACHER');
  const isSuperAdmin = (user?.roles ?? []).some((role) => role.name === 'SUPER_ADMIN');
  const { schools, loading: schoolsLoading, selectedSchool, selectSchool, error: schoolError } = useSchool();
  const canChooseSchool = isSuperAdmin || schools.length > 1;
  const [counts,setCounts]=useState<Counts>({students:null,guardians:null,staff:null,enrollments:null});
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const activeSchoolIdRef=useRef<string|null>(selectedSchool?.id??null);
  const requestIdRef=useRef(0);
  activeSchoolIdRef.current=selectedSchool?.id??null;
  useEffect(()=>{requestIdRef.current+=1;setCounts({students:null,guardians:null,staff:null,enrollments:null});setError(null);setLoading(false);},[selectedSchool?.id]);
  const loadCounts=useCallback(async()=>{
    const requestId=++requestIdRef.current;
    if(!selectedSchool){setCounts({students:null,guardians:null,staff:null,enrollments:null});setLoading(false);return;}
    const schoolId=selectedSchool.id;setLoading(true);setError(null);const query={school_id:schoolId,limit:MAX_COUNT_FETCH};
    const [students,guardians,staff,enrollments]=await Promise.allSettled([
      api.get<StudentResponse[]>('/api/v1/students',query),api.get<GuardianResponse[]>('/api/v1/guardians',query),
      api.get<StaffResponse[]>('/api/v1/staff',query),api.get<EnrollmentResponse[]>('/api/v1/enrollments',query),
    ]);
    if(activeSchoolIdRef.current!==schoolId||requestIdRef.current!==requestId)return;
    setCounts({students:students.status==='fulfilled'?students.value.length:null,guardians:guardians.status==='fulfilled'?guardians.value.length:null,staff:staff.status==='fulfilled'?staff.value.length:null,enrollments:enrollments.status==='fulfilled'?enrollments.value.length:null});
    if(students.status==='rejected'&&students.reason instanceof ApiError&&students.reason.status===403)setError('You do not have access to view records for this school.');
    setLoading(false);
  },[selectedSchool]);
  useEffect(()=>{void loadCounts();},[loadCounts]);
  const countCards=[{label:'Students',value:counts.students,to:'/students'},{label:'Guardians',value:counts.guardians,to:'/guardians'},{label:'Staff',value:counts.staff,to:'/staff'},{label:'Enrollments',value:counts.enrollments,to:'/enrollments'}].filter(c=>!isTeacher||['Students','Enrollments'].includes(c.label));
  return <div>
    <PageHeader title={`Welcome, ${user?.first_name??''}`} subtitle={selectedSchool? `Viewing data for ${selectedSchool.name}`:canChooseSchool?'Choose a school below to open its dashboard and records.':'Your assigned school is being loaded.'} actions={selectedSchool&&canChooseSchool?<Button variant="secondary" onClick={()=>selectSchool('')}>← Back to school selection</Button>:undefined}/>
    {schoolError&&<ErrorBanner message={schoolError}/>}
    {!selectedSchool?<section className="mt-2"><h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Select a school</h2><p className="mb-4 text-sm text-slate-500">Choose a school card to open its dashboard.</p>{schoolsLoading?<Spinner label="Loading your schools…"/>:schools.length===1&&!isSuperAdmin?<Spinner label="Opening your assigned school…"/>:schools.length===0?<Card className="p-6">No schools are available to your account yet. Ask a platform administrator to assign you to a school.</Card>:<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{schools.map(s=><button key={s.id} type="button" disabled={!s.is_active} onClick={()=>selectSchool(s.id)} className="rounded-lg text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600 disabled:opacity-60"><Card className="h-full p-5 transition-all hover:-translate-y-0.5 hover:shadow-md"><p className="font-semibold text-slate-900">{s.name}</p><p className="mt-1 text-sm text-slate-500">School code: {s.code}</p><p className="mt-2 text-xs font-semibold text-indigo-700">{s.is_active?'Open school →':'Inactive'}</p></Card></button>)}</div>}</section>:isTeacher?<TeacherDashboard schoolId={selectedSchool.id}/>:loading?<Spinner/>:<><div className="mb-3 flex justify-end"><Button variant="secondary" onClick={()=>void loadCounts()}>Refresh counts</Button></div>{error&&<ErrorBanner message={error}/>}<AdminSchoolOverview schoolId={selectedSchool.id}/><div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">{countCards.map(c=><Link key={c.label} to={c.to}><Card className="p-5 transition-shadow hover:shadow-md"><p className="text-sm font-medium text-slate-500">{c.label}</p><p className="mt-2 text-3xl font-semibold text-slate-900">{c.value===null?'—':c.value}</p><p className="mt-1 text-xs text-slate-400">{c.value===MAX_COUNT_FETCH?`${MAX_COUNT_FETCH}+ records (page cap reached)`:'from live school data'}</p></Card></Link>)}</div></>}
  </div>;
}
