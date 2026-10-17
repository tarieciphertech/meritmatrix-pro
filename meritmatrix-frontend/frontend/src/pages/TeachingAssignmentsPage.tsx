import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { ClassResponse, ClassSubjectResponse, StaffResponse } from '../types';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

type Assignment = { id:string; staff_id:string; class_subject_id:string; start_date:string; end_date?:string|null; is_primary:boolean; is_active:boolean; staff_name?:string|null; class_name?:string|null; class_code?:string|null; subject_name?:string|null; subject_code?:string|null };
type Form = { staff_id:string; class_subject_id:string; start_date:string; end_date:string; is_primary:boolean; notes:string };
const today = new Date().toISOString().slice(0,10);
const initial:Form = {staff_id:'',class_subject_id:'',start_date:today,end_date:'',is_primary:false,notes:''};

export default function TeachingAssignmentsPage() {
 const {selectedSchool}=useSchool(); const [staff,setStaff]=useState<StaffResponse[]>([]); const [classes,setClasses]=useState<ClassResponse[]>([]); const [pairs,setPairs]=useState<ClassSubjectResponse[]>([]); const [items,setItems]=useState<Assignment[]>([]); const [form,setForm]=useState<Form>(initial); const [show,setShow]=useState(false); const [loading,setLoading]=useState(false); const [saving,setSaving]=useState(false); const [error,setError]=useState<string|null>(null); const [notice,setNotice]=useState('');
 const activeSchoolIdRef=useRef<string|null>(selectedSchool?.id??null); const loadRequestIdRef=useRef(0);
 const load=useCallback(async()=>{
  if(!selectedSchool){setStaff([]);setClasses([]);setPairs([]);setItems([]);setLoading(false);return;}
  const requestSchoolId=selectedSchool.id; const requestId=++loadRequestIdRef.current;
  setStaff([]);setClasses([]);setPairs([]);setItems([]);setLoading(true);setError(null);
  try{
   const [staffRows,classRows,assignmentRows]=await Promise.all([
    api.get<StaffResponse[]>('/api/v1/staff',{school_id:requestSchoolId,limit:200}),
    api.get<ClassResponse[]>('/api/v1/classes',{school_id:requestSchoolId}),
    api.get<Assignment[]>('/api/v1/teaching-assignments',{school_id:requestSchoolId}),
   ]);
   if(activeSchoolIdRef.current!==requestSchoolId||loadRequestIdRef.current!==requestId)return;
   const groups=await Promise.all(classRows.map(c=>api.get<ClassSubjectResponse[]>('/api/v1/class-subjects',{class_id:c.id}).catch(()=>[] as ClassSubjectResponse[])));
   if(activeSchoolIdRef.current!==requestSchoolId||loadRequestIdRef.current!==requestId)return;
   setStaff(staffRows.filter(x=>x.is_active&&x.employment_status==='active'));
   setClasses(classRows.filter(x=>x.is_active));setPairs(groups.flat());setItems(assignmentRows);
  }catch(e){
   if(activeSchoolIdRef.current===requestSchoolId&&loadRequestIdRef.current===requestId){setStaff([]);setClasses([]);setPairs([]);setItems([]);setError(e instanceof Error?e.message:'Could not load assignments');}
  }finally{
   if(activeSchoolIdRef.current===requestSchoolId&&loadRequestIdRef.current===requestId)setLoading(false);
  }
 },[selectedSchool]);
 useEffect(()=>{
  activeSchoolIdRef.current=selectedSchool?.id??null;loadRequestIdRef.current+=1;
  setStaff([]);setClasses([]);setPairs([]);setItems([]);setForm({...initial,start_date:today});setShow(false);setError(null);setNotice('');
 },[selectedSchool?.id]);
 useEffect(()=>{void load();},[load]);
 async function submit(e:FormEvent){e.preventDefault();if(!selectedSchool)return;setSaving(true);setError(null);try{await api.post('/api/v1/teaching-assignments',{staff_id:form.staff_id,class_subject_id:form.class_subject_id,start_date:form.start_date,end_date:form.end_date||null,is_primary:form.is_primary,notes:form.notes||null},{school_id:selectedSchool.id});setForm({...initial,start_date:today});setShow(false);setNotice('Teacher assigned successfully.');await load();}catch(e){setError(e instanceof ApiError?e.message:e instanceof Error?e.message:'Could not assign teacher');}finally{setSaving(false);}}
 async function end(item:Assignment){if(!window.confirm('End this teaching assignment?'))return;try{await api.delete('/api/v1/teaching-assignments/'+item.id);await load();}catch(e){setError(e instanceof Error?e.message:'Could not end assignment');}}
 if(!selectedSchool)return <div><PageHeader title="Teacher Assignments"/><Card className="p-6">Select a school first.</Card></div>;
 return <div className="space-y-5"><PageHeader title="Teacher Assignments" subtitle={`Assign staff to class subjects at ${selectedSchool.name}`} actions={<Button onClick={()=>setShow(!show)}>{show?'Cancel':'+ Assign teacher'}</Button>}/>{error&&<ErrorBanner message={error} onRetry={load} />}{notice&&<div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
 {show&&<Card className="p-5"><form onSubmit={submit} className="space-y-4"><h2 className="font-semibold">New teaching assignment</h2><div className="grid gap-4 sm:grid-cols-2"><label className="text-sm">Teacher<select required value={form.staff_id} onChange={e=>setForm({...form,staff_id:e.target.value})} className="mt-1 block w-full rounded-md border p-2"><option value="">Select staff member…</option>{staff.map(s=><option key={s.id} value={s.id}>{s.first_name} {s.last_name} · {s.staff_number}</option>)}</select></label><label className="text-sm">Class and subject<select required value={form.class_subject_id} onChange={e=>setForm({...form,class_subject_id:e.target.value})} className="mt-1 block w-full rounded-md border p-2"><option value="">Select class subject…</option>{pairs.filter(p=>classes.some(c=>c.id===p.class_id)).map(p=><option key={p.id} value={p.id}>{p.class_name||classes.find(c=>c.id===p.class_id)?.name} · {p.subject_name||p.subject_code}</option>)}</select></label><label className="text-sm">Start date<input required type="date" value={form.start_date} onChange={e=>setForm({...form,start_date:e.target.value})} className="mt-1 block w-full rounded-md border p-2"/></label><label className="text-sm">End date (optional)<input type="date" min={form.start_date} value={form.end_date} onChange={e=>setForm({...form,end_date:e.target.value})} className="mt-1 block w-full rounded-md border p-2"/></label></div><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_primary} onChange={e=>setForm({...form,is_primary:e.target.checked})}/>Primary teacher for this class subject</label><label className="block text-sm">Notes<textarea rows={2} value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} className="mt-1 block w-full rounded-md border p-2"/></label><div className="flex justify-end"><Button type="submit" disabled={saving||!staff.length||!pairs.length}>{saving?'Saving…':'Save assignment'}</Button></div>{!staff.length&&<p className="text-sm text-amber-700">Add active staff first.</p>}{!pairs.length&&<p className="text-sm text-amber-700">Assign subjects to classes in Academic Setup first.</p>}</form></Card>}
 {loading?<Spinner/>:items.length===0?<Card className="p-8 text-center"><h2 className="font-semibold">No teacher assignments yet</h2><p className="mt-2 text-sm text-slate-600">Create staff, classes, subjects, and class-subject links first.</p></Card>:<Card className="divide-y">{items.map(a=><div key={a.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="font-semibold">{a.staff_name||'Teacher'}</h3><p className="text-sm text-slate-600">{a.class_name||a.class_code} · {a.subject_name||a.subject_code}</p><p className="text-xs text-slate-500">From {a.start_date}{a.end_date?' until '+a.end_date:' · no end date'}{a.is_primary?' · Primary teacher':''}</p></div><div className="flex items-center gap-2"><span className="text-xs">{a.is_active?'Active':'Ended'}</span>{a.is_active&&<Button variant="danger" onClick={()=>void end(a)}>End assignment</Button>}</div></div>)}</Card>}
 <Card className="p-4"><p className="text-sm text-slate-600">Assignments are restricted to this school. Attendance and assessments will use these relationships in later modules.</p></Card></div>;
}
