import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { AcademicYearResponse, ClassResponse, ClassSubjectResponse, SubjectResponse, TermResponse } from '../types';
import { Badge, Button, Card, EmptyState, ErrorBanner, Field, Input, Modal, PageHeader, Select, Spinner, Table, Td } from '../components/ui';

type Tab = 'years' | 'terms' | 'classes' | 'subjects' | 'class-subjects';
type YearForm = { name: string; start_date: string; end_date: string; is_current: boolean };
type TermForm = { name: string; term_number: string; start_date: string; end_date: string; is_current: boolean };
type ClassForm = { name: string; code: string; level: string; stream: string; description: string };
type SubjectForm = { name: string; code: string; description: string };
const tabs: {id: Tab; label: string}[] = [{id:'years',label:'Academic Years'},{id:'terms',label:'Terms'},{id:'classes',label:'Classes'},{id:'subjects',label:'Subjects'},{id:'class-subjects',label:'Class Subjects'}];
const emptyYear: YearForm = {name:'',start_date:'',end_date:'',is_current:false};
const emptyTerm: TermForm = {name:'',term_number:'1',start_date:'',end_date:'',is_current:false};
const emptyClass: ClassForm = {name:'',code:'',level:'',stream:'',description:''};
const emptySubject: SubjectForm = {name:'',code:'',description:''};

export default function AcademicSetupPage() {
 const {selectedSchool}=useSchool();
 const [tab,setTab]=useState<Tab>('years');
 const [years,setYears]=useState<AcademicYearResponse[]>([]);
 const [terms,setTerms]=useState<TermResponse[]>([]);
 const [classes,setClasses]=useState<ClassResponse[]>([]);
 const [subjects,setSubjects]=useState<SubjectResponse[]>([]);
 const [assignments,setAssignments]=useState<ClassSubjectResponse[]>([]);
 const [selectedClassId,setSelectedClassId]=useState('');
 const [selectedSubjectId,setSelectedSubjectId]=useState('');
 const [assigning,setAssigning]=useState(false);
 const [yearId,setYearId]=useState('');
 const [loading,setLoading]=useState(false);
 const [saving,setSaving]=useState(false);
 const [error,setError]=useState<string|null>(null);
 const [formError,setFormError]=useState<string|null>(null);
 const [open,setOpen]=useState(false);
 const [editingId,setEditingId]=useState<string|null>(null);
 const [yf,setYf]=useState<YearForm>(emptyYear);
 const [tf,setTf]=useState<TermForm>(emptyTerm);
 const [cf,setCf]=useState<ClassForm>(emptyClass);
 const [sf,setSf]=useState<SubjectForm>(emptySubject);

 const load=useCallback(async()=>{
  if(!selectedSchool){setYears([]);setTerms([]);setClasses([]);setSubjects([]);return;}
  setLoading(true);setError(null);
  try{
   const [ys,cs,ss]=await Promise.all([
    api.get<AcademicYearResponse[]>('/api/v1/academic-years',{school_id:selectedSchool.id}),
    api.get<ClassResponse[]>('/api/v1/classes',{school_id:selectedSchool.id}),
    api.get<SubjectResponse[]>('/api/v1/subjects',{school_id:selectedSchool.id})
   ]);
   setYears(ys);setClasses(cs);setSubjects(ss);
   setSelectedClassId(current=>cs.some(x=>x.id===current)?current:(cs.find(x=>x.is_active)?.id||''));
   const chosen=ys.find(y=>y.id===yearId)||ys.find(y=>y.is_current)||ys[0];
   setYearId(chosen?.id||'');
   const groups=await Promise.all(ys.map(y=>api.get<TermResponse[]>('/api/v1/terms',{academic_year_id:y.id}).catch(()=>[] as TermResponse[])));
   setTerms(groups.flat());
  }catch(e){setError(e instanceof Error?e.message:'Could not load academic setup');}
  finally{setLoading(false);}
 },[selectedSchool,yearId]);
 useEffect(()=>{void load();},[load]);
 useEffect(()=>{
  if(!selectedClassId){setAssignments([]);return;}
  let cancelled=false;
  api.get<ClassSubjectResponse[]>('/api/v1/class-subjects',{class_id:selectedClassId})
   .then(items=>{if(!cancelled)setAssignments(items);})
   .catch(e=>{if(!cancelled)setError(e instanceof Error?e.message:'Could not load class subjects');});
  return ()=>{cancelled=true;};
 },[selectedClassId]);
 async function assignSubject(){
  if(!selectedClassId||!selectedSubjectId)return;
  setAssigning(true);setError(null);
  try{
   await api.post('/api/v1/class-subjects',{class_id:selectedClassId,subject_id:selectedSubjectId});
   setSelectedSubjectId('');
   setAssignments(await api.get<ClassSubjectResponse[]>('/api/v1/class-subjects',{class_id:selectedClassId}));
  }catch(e){setError(e instanceof Error?e.message:'Could not assign subject to class');}
  finally{setAssigning(false);}
 }
 async function removeAssignment(item:ClassSubjectResponse){
  if(!window.confirm('Remove '+(item.subject_name||'this subject')+' from '+(item.class_name||'this class')+'?'))return;
  try{await api.delete('/api/v1/class-subjects/'+item.id);setAssignments(await api.get<ClassSubjectResponse[]>('/api/v1/class-subjects',{class_id:selectedClassId}));}
  catch(e){setError(e instanceof Error?e.message:'Could not remove class subject');}
 }

 function create(){
  setEditingId(null);setFormError(null);setYf(emptyYear);setTf(emptyTerm);setCf(emptyClass);setSf(emptySubject);setOpen(true);
 }
 function editYear(x:AcademicYearResponse){setEditingId(x.id);setYf({name:x.name,start_date:x.start_date,end_date:x.end_date,is_current:x.is_current});setFormError(null);setOpen(true);}
 function editTerm(x:TermResponse){setEditingId(x.id);setYearId(x.academic_year_id);setTf({name:x.name,term_number:String(x.term_number),start_date:x.start_date,end_date:x.end_date,is_current:x.is_current});setFormError(null);setOpen(true);}
 function editClass(x:ClassResponse){setEditingId(x.id);setCf({name:x.name,code:x.code,level:x.level==null?'':String(x.level),stream:x.stream||'',description:x.description||''});setFormError(null);setOpen(true);}
 function editSubject(x:SubjectResponse){setEditingId(x.id);setSf({name:x.name,code:x.code,description:x.description||''});setFormError(null);setOpen(true);}

 async function submit(e:FormEvent){
  e.preventDefault();if(!selectedSchool)return;setSaving(true);setFormError(null);
  try{
   if(tab==='years'){
    const p={name:yf.name.trim(),start_date:yf.start_date,end_date:yf.end_date};
    if(editingId) await api.patch('/api/v1/academic-years/'+editingId,{...p,is_current:yf.is_current});
    else await api.post('/api/v1/academic-years',p,{school_id:selectedSchool.id});
   }else if(tab==='terms'){
    if(!yearId)throw new Error('Select an academic year first.');
    const p={name:tf.name.trim(),term_number:Number(tf.term_number),start_date:tf.start_date,end_date:tf.end_date};
    if(editingId)await api.patch('/api/v1/terms/'+editingId,{...p,is_current:tf.is_current});
    else await api.post('/api/v1/terms',p,{academic_year_id:yearId});
   }else if(tab==='classes'){
    const p={name:cf.name.trim(),code:cf.code.trim(),level:cf.level===''?null:Number(cf.level),stream:cf.stream.trim()||null,description:cf.description.trim()||null};
    if(editingId)await api.patch('/api/v1/classes/'+editingId,p);
    else await api.post('/api/v1/classes',p,{school_id:selectedSchool.id});
   }else{
    const p={name:sf.name.trim(),code:sf.code.trim(),description:sf.description.trim()||null};
    if(editingId)await api.patch('/api/v1/subjects/'+editingId,p);
    else await api.post('/api/v1/subjects',p,{school_id:selectedSchool.id});
   }
   setOpen(false);await load();
  }catch(e){setFormError(e instanceof ApiError||e instanceof Error?e.message:'Could not save record');}
  finally{setSaving(false);}
 }
 async function deactivate(kind:Tab,id:string,label:string){
  if(!window.confirm('Deactivate "'+label+'"? Existing records will be retained.'))return;
  const endpoint=kind==='years'?'academic-years':kind;
  try{await api.delete('/api/v1/'+endpoint+'/'+id);await load();}
  catch(e){setError(e instanceof Error?e.message:'Could not deactivate record');}
 }
 const activeYears=years.filter(x=>x.is_active);
 const rows=tab==='terms'?terms.filter(t=>t.academic_year_id===yearId):terms;

 return <div>
  <PageHeader title="Academic Setup" subtitle={selectedSchool?'Configure the academic structure for '+selectedSchool.name:'Select a school to continue'} actions={selectedSchool&&tab!=='class-subjects'&&<Button onClick={create}>+ Add {tab==='years'?'Academic Year':tab==='terms'?'Term':tab==='classes'?'Class':'Subject'}</Button>}/>
  <div className="mb-5 flex flex-wrap gap-2">{tabs.map(x=><Button key={x.id} variant={tab===x.id?'primary':'secondary'} onClick={()=>{setTab(x.id);setOpen(false);setEditingId(null);}}>{x.label}</Button>)}</div>
  {!selectedSchool&&<Card><EmptyState title="No school selected" hint="Choose a school from the selector in the header."/></Card>}
  {selectedSchool&&error&&<ErrorBanner message={error} onRetry={load}/>}
  {selectedSchool&&loading&&<Spinner label="Loading academic setup…"/>}
  {selectedSchool&&!loading&&tab==='years'&&<Card>{years.length===0?<EmptyState title="No academic years yet" hint="Create an academic year before adding terms and enrollments."/>:<Table headers={['Name','Start','End','Current','Status','Actions']}>{years.map(x=><tr key={x.id}><Td className="font-medium">{x.name}</Td><Td>{x.start_date}</Td><Td>{x.end_date}</Td><Td>{x.is_current?<Badge tone="green">Current</Badge>:'—'}</Td><Td><Badge tone={x.is_active?'green':'slate'}>{x.is_active?'Active':'Inactive'}</Badge></Td><Td><div className="flex gap-2"><Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={()=>editYear(x)}>Edit</Button>{x.is_active&&<Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void deactivate('years',x.id,x.name)}>Deactivate</Button>}</div></Td></tr>)}</Table>}</Card>}
  {selectedSchool&&!loading&&tab==='terms'&&<div className="space-y-3"><Card><div className="p-4"><Field label="Academic year" required><Select value={yearId} onChange={e=>setYearId(e.target.value)}><option value="">Select academic year…</option>{activeYears.map(x=><option key={x.id} value={x.id}>{x.name}{x.is_current?' (Current)':''}</option>)}</Select></Field></div></Card><Card>{rows.length===0?<EmptyState title="No terms for this year" hint="Select an academic year and create its first term."/>:<Table headers={['Term','Number','Start','End','Current','Status','Actions']}>{rows.map(x=><tr key={x.id}><Td className="font-medium">{x.name}</Td><Td>{x.term_number}</Td><Td>{x.start_date}</Td><Td>{x.end_date}</Td><Td>{x.is_current?<Badge tone="green">Current</Badge>:'—'}</Td><Td><Badge tone={x.is_active?'green':'slate'}>{x.is_active?'Active':'Inactive'}</Badge></Td><Td><div className="flex gap-2"><Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={()=>editTerm(x)}>Edit</Button>{x.is_active&&<Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void deactivate('terms',x.id,x.name)}>Deactivate</Button>}</div></Td></tr>)}</Table>}</Card></div>}
  {selectedSchool&&!loading&&tab==='classes'&&<Card>{classes.length===0?<EmptyState title="No classes yet" hint="Add classes such as Form 1, Form 2 or Grade 7."/>:<Table headers={['Name','Code','Level','Stream','Status','Actions']}>{classes.map(x=><tr key={x.id}><Td className="font-medium">{x.name}</Td><Td>{x.code}</Td><Td>{x.level??'—'}</Td><Td>{x.stream||'—'}</Td><Td><Badge tone={x.is_active?'green':'slate'}>{x.is_active?'Active':'Inactive'}</Badge></Td><Td><div className="flex gap-2"><Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={()=>editClass(x)}>Edit</Button>{x.is_active&&<Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void deactivate('classes',x.id,x.name)}>Deactivate</Button>}</div></Td></tr>)}</Table>}</Card>}
  {selectedSchool&&!loading&&tab==='class-subjects'&&<div className="space-y-3"><Card><div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-3"><Field label="Class" required><Select value={selectedClassId} onChange={e=>setSelectedClassId(e.target.value)}><option value="">Select class…</option>{classes.filter(x=>x.is_active).map(x=><option key={x.id} value={x.id}>{x.name} ({x.code})</option>)}</Select></Field><Field label="Subject to assign" required><Select value={selectedSubjectId} onChange={e=>setSelectedSubjectId(e.target.value)}><option value="">Select subject…</option>{subjects.filter(x=>x.is_active&&!assignments.some(a=>a.subject_id===x.id)).map(x=><option key={x.id} value={x.id}>{x.name} ({x.code})</option>)}</Select></Field><div className="flex items-end"><Button disabled={!selectedClassId||!selectedSubjectId||assigning} onClick={()=>void assignSubject()}>{assigning?'Assigning…':'Assign subject'}</Button></div></div></Card><Card>{!selectedClassId?<EmptyState title="No classes available" hint="Create a class before assigning subjects."/>:assignments.length===0?<EmptyState title="No subjects assigned" hint="Choose a subject above and assign it to this class."/>:<Table headers={['Subject','Code','Actions']}>{assignments.map(x=><tr key={x.id}><Td className="font-medium">{x.subject_name||subjects.find(s=>s.id===x.subject_id)?.name||'Subject'}</Td><Td>{x.subject_code||subjects.find(s=>s.id===x.subject_id)?.code||'—'}</Td><Td><Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void removeAssignment(x)}>Remove</Button></Td></tr>)}</Table>}</Card></div>}
  {selectedSchool&&!loading&&tab==='subjects'&&<Card>{subjects.length===0?<EmptyState title="No subjects yet" hint="Add subjects such as Mathematics, English or Science."/>:<Table headers={['Subject','Code','Description','Status','Actions']}>{subjects.map(x=><tr key={x.id}><Td className="font-medium">{x.name}</Td><Td>{x.code}</Td><Td>{x.description||'—'}</Td><Td><Badge tone={x.is_active?'green':'slate'}>{x.is_active?'Active':'Inactive'}</Badge></Td><Td><div className="flex gap-2"><Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={()=>editSubject(x)}>Edit</Button>{x.is_active&&<Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void deactivate('subjects',x.id,x.name)}>Deactivate</Button>}</div></Td></tr>)}</Table>}</Card>}
  <Modal open={open} title={(editingId?'Edit ':'New ')+(tab==='years'?'Academic Year':tab==='terms'?'Term':tab==='classes'?'Class':'Subject')} onClose={()=>setOpen(false)}>
   <form onSubmit={submit} className="space-y-4">{formError&&<ErrorBanner message={formError}/>}
   {tab==='years'&&<><Field label="Academic year name" required><Input required maxLength={100} value={yf.name} onChange={e=>setYf(p=>({...p,name:e.target.value}))} placeholder="2026 Academic Year"/></Field><div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Field label="Start date" required><Input required type="date" value={yf.start_date} onChange={e=>setYf(p=>({...p,start_date:e.target.value}))}/></Field><Field label="End date" required><Input required type="date" min={yf.start_date||undefined} value={yf.end_date} onChange={e=>setYf(p=>({...p,end_date:e.target.value}))}/></Field></div>{editingId&&<label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={yf.is_current} onChange={e=>setYf(p=>({...p,is_current:e.target.checked}))}/> Set as current year</label>}</>}
   {tab==='terms'&&<><Field label="Academic year" required><Select required value={yearId} onChange={e=>setYearId(e.target.value)}><option value="">Select year…</option>{activeYears.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</Select></Field><Field label="Term name" required><Input required value={tf.name} onChange={e=>setTf(p=>({...p,name:e.target.value}))} placeholder="Term 1"/></Field><Field label="Term number" required><Input required type="number" min="1" step="1" value={tf.term_number} onChange={e=>setTf(p=>({...p,term_number:e.target.value}))}/></Field><div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Field label="Start date" required><Input required type="date" value={tf.start_date} onChange={e=>setTf(p=>({...p,start_date:e.target.value}))}/></Field><Field label="End date" required><Input required type="date" min={tf.start_date||undefined} value={tf.end_date} onChange={e=>setTf(p=>({...p,end_date:e.target.value}))}/></Field></div>{editingId&&<label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={tf.is_current} onChange={e=>setTf(p=>({...p,is_current:e.target.checked}))}/> Set as current term</label>}</>}
   {tab==='classes'&&<><Field label="Class name" required><Input required maxLength={100} value={cf.name} onChange={e=>setCf(p=>({...p,name:e.target.value}))} placeholder="Form 1"/></Field><div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><Field label="Class code" required><Input required maxLength={50} value={cf.code} onChange={e=>setCf(p=>({...p,code:e.target.value}))} placeholder="F1"/></Field><Field label="Level"><Input type="number" min="0" step="1" value={cf.level} onChange={e=>setCf(p=>({...p,level:e.target.value}))}/></Field></div><Field label="Stream"><Input value={cf.stream} onChange={e=>setCf(p=>({...p,stream:e.target.value}))} placeholder="A"/></Field><Field label="Description"><Input value={cf.description} onChange={e=>setCf(p=>({...p,description:e.target.value}))}/></Field></>}
   {tab==='subjects'&&<><Field label="Subject name" required><Input required maxLength={100} value={sf.name} onChange={e=>setSf(p=>({...p,name:e.target.value}))} placeholder="Mathematics"/></Field><Field label="Subject code" required><Input required maxLength={20} value={sf.code} onChange={e=>setSf(p=>({...p,code:e.target.value}))} placeholder="MATH"/></Field><Field label="Description"><Input value={sf.description} onChange={e=>setSf(p=>({...p,description:e.target.value}))}/></Field></>}
   <div className="flex justify-end gap-2 pt-2"><Button variant="secondary" onClick={()=>setOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>{saving?'Saving…':editingId?'Save Changes':'Create'}</Button></div></form>
  </Modal>
 </div>;
}
