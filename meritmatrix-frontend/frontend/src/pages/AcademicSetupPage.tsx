import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { AcademicYearResponse, ClassResponse, ClassSubjectResponse, InstitutionType, SubjectResponse, TermResponse } from '../types';
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

type SubjectTemplate = { name: string; code: string; description: string };

function getSubjectTemplates(institutionType?: InstitutionType | null, countryCode?: string | null): SubjectTemplate[] {
 const early: SubjectTemplate[] = [
  {name:'Language and Literacy',code:'LIT',description:'Early language development and communication'},
  {name:'Mathematics and Numeracy',code:'NUM',description:'Early mathematical concepts and numeracy'},
  {name:'Environmental Awareness',code:'ENV',description:'Awareness of the natural and social environment'},
  {name:'Creative Arts',code:'ART',description:'Creative expression, music and art'},
  {name:'Physical Development',code:'PHYDEV',description:'Movement, coordination and physical development'},
  {name:'Social and Emotional Learning',code:'SEL',description:'Social skills and emotional development'},
 ];
 const primary: SubjectTemplate[] = countryCode === 'BW' ? [
  {name:'English',code:'ENG',description:'English language and literacy'},
  {name:'Setswana',code:'SETS',description:'Setswana language and literacy'},
  {name:'Mathematics',code:'MATH',description:'Primary mathematics and numeracy'},
  {name:'Science',code:'SCI',description:'Primary science'},
  {name:'Social Studies',code:'SOC',description:'People, society and environment'},
  {name:'Agriculture',code:'AGRI',description:'Primary agriculture'},
  {name:'Religious Education',code:'RE',description:'Religious and moral education'},
  {name:'Creative and Performing Arts',code:'CPA',description:'Visual arts, music and performance'},
  {name:'Physical Education',code:'PE',description:'Physical education and wellbeing'},
  {name:'Information and Communications Technology',code:'ICT',description:'Digital literacy and computing'},
 ] : [
  {name:'English Language',code:'ENG',description:'English language and literacy'},
  {name:'Mathematics',code:'MATH',description:'Primary mathematics and numeracy'},
  {name:'Indigenous Language',code:'LANG',description:'School-selected indigenous language (for example Shona, Ndebele or Tonga)'},
  {name:'Environmental Science',code:'ENVSCI',description:'Primary environmental science'},
  {name:'Heritage and Social Studies',code:'HSS',description:'Heritage, citizenship, history and social studies'},
  {name:'Agriculture',code:'AGRI',description:'Primary agriculture'},
  {name:'Religious and Moral Education',code:'RME',description:'Religious and moral education'},
  {name:'Physical Education',code:'PE',description:'Physical education and wellbeing'},
  {name:'Visual and Performing Arts',code:'VPA',description:'Visual arts, music and performance'},
  {name:'Information and Communications Technology',code:'ICT',description:'Digital literacy and computing'},
 ];
 const secondary: SubjectTemplate[] = [
  {name:'English Language',code:'ENG',description:'English language'},
  {name:'Mathematics',code:'MATH',description:'Mathematics'},
  {name:'Indigenous Language',code:'LANG',description:'School-selected indigenous language'},
  {name:'Combined Science',code:'COMSCI',description:'Integrated science course'},
  {name:'Biology',code:'BIO',description:'Biology'},
  {name:'Chemistry',code:'CHEM',description:'Chemistry'},
  {name:'Physics',code:'PHY',description:'Physics'},
  {name:'Geography',code:'GEO',description:'Geography'},
  {name:'History',code:'HIST',description:'History'},
  {name:'Heritage Studies',code:'HER',description:'Heritage studies and citizenship'},
  {name:'Commerce',code:'COMM',description:'Commerce and business fundamentals'},
  {name:'Accounting',code:'ACC',description:'Accounting'},
  {name:'Computer Science',code:'CS',description:'Computer science and programming'},
  {name:'Agriculture',code:'AGRI',description:'Agriculture'},
  {name:'Family and Religious Studies',code:'FRS',description:'Family and religious studies'},
  {name:'Physical Education',code:'PE',description:'Physical education and wellbeing'},
 ];
 const advanced: SubjectTemplate[] = [
  {name:'Pure Mathematics',code:'PMATH',description:'Advanced level pure mathematics'},
  {name:'Economics',code:'ECON',description:'Economics'},
  {name:'Literature in English',code:'LITENG',description:'Literature in English'},
 ];
 switch (institutionType) {
  case 'early_childhood': return early;
  case 'primary': return primary;
  case 'secondary': return secondary;
  case 'high_school': return [...secondary, ...advanced];
  case 'combined': return [...primary, ...secondary, ...advanced];
  default: return [];
 }
}

type ClassTemplate = { name: string; code: string; level: number; description: string };
function getClassTemplates(institutionType?: InstitutionType | null): ClassTemplate[] {
 const primary: ClassTemplate[] = [
  {name:'ECG',code:'ECG',level:0,description:'Early childhood group'},
  ...Array.from({length:7},(_,i)=>({name:'Grade '+(i+1),code:'G'+(i+1),level:i+1,description:'Primary grade '+(i+1)})),
 ];
 const secondary: ClassTemplate[] = Array.from({length:4},(_,i)=>({name:'Form '+(i+1),code:'F'+(i+1),level:i+1,description:'Secondary form '+(i+1)}));
 const high: ClassTemplate[] = Array.from({length:6},(_,i)=>({name:'Form '+(i+1),code:'F'+(i+1),level:i+1,description:'High school form '+(i+1)}));
 switch(institutionType){
  case 'early_childhood': return primary.slice(0,1);
  case 'primary': return primary;
  case 'secondary': return secondary;
  case 'high_school': return high;
  case 'combined': return [...primary,...high];
  default: return [];
 }
}

export default function AcademicSetupPage() {
 const {selectedSchool}=useSchool();
 const classTemplates=getClassTemplates(selectedSchool?.institution_type);
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
 const activeSchoolIdRef=useRef<string|null>(selectedSchool?.id??null);
 const loadRequestIdRef=useRef(0);
 activeSchoolIdRef.current=selectedSchool?.id??null;
 useEffect(()=>{
  loadRequestIdRef.current+=1;
  setYears([]);setTerms([]);setClasses([]);setSubjects([]);setAssignments([]);
  setSelectedClassId('');setSelectedSubjectId('');setYearId('');setError(null);
  setLoading(false);
 },[selectedSchool?.id]);

 const load=useCallback(async()=>{
  const requestId=++loadRequestIdRef.current;
  if(!selectedSchool){setYears([]);setTerms([]);setClasses([]);setSubjects([]);setAssignments([]);setLoading(false);return;}
  const requestSchoolId=selectedSchool.id;
  setLoading(true);setError(null);
  try{
   const [ys,cs,ss]=await Promise.all([
    api.get<AcademicYearResponse[]>('/api/v1/academic-years',{school_id:requestSchoolId}),
    api.get<ClassResponse[]>('/api/v1/classes',{school_id:requestSchoolId}),
    api.get<SubjectResponse[]>('/api/v1/subjects',{school_id:requestSchoolId})
   ]);
   if(activeSchoolIdRef.current!==requestSchoolId||loadRequestIdRef.current!==requestId)return;
   setYears(ys);setClasses(cs);setSubjects(ss);
   setSelectedClassId(current=>cs.some(x=>x.id===current)?current:(cs.find(x=>x.is_active)?.id||''));
   const chosen=ys.find(y=>y.id===yearId)||ys.find(y=>y.is_current)||ys[0];
   setYearId(chosen?.id||'');
   const groups=await Promise.all(ys.map(y=>api.get<TermResponse[]>('/api/v1/terms',{academic_year_id:y.id}).catch(()=>[] as TermResponse[])));
   if(activeSchoolIdRef.current!==requestSchoolId||loadRequestIdRef.current!==requestId)return;
   setTerms(groups.flat());
  }catch(e){if(activeSchoolIdRef.current===selectedSchool?.id&&loadRequestIdRef.current===requestId)setError(e instanceof Error?e.message:'Could not load academic setup');}
  finally{if(activeSchoolIdRef.current===selectedSchool?.id&&loadRequestIdRef.current===requestId)setLoading(false);}
 },[selectedSchool,yearId]);
 useEffect(()=>{void load();},[load]);
 useEffect(()=>{
  if(!selectedClassId||!selectedSchool){setAssignments([]);return;}
  let cancelled=false;
  api.get<ClassSubjectResponse[]>('/api/v1/class-subjects',{class_id:selectedClassId})
   .then(items=>{if(!cancelled)setAssignments(items);})
   .catch(e=>{if(!cancelled)setError(e instanceof Error?e.message:'Could not load class subjects');});
  return ()=>{cancelled=true;};
 },[selectedClassId,selectedSchool?.id]);
 async function applyClassTemplate(){
  if(!selectedSchool)return;
  if(classTemplates.length===0){
   setError('Set this school\'s institution type in Schools before generating standard classes.');
   return;
  }
  const existing=new Set(classes.flatMap(item=>[item.code.trim().toUpperCase(),item.name.trim().toUpperCase()]));
  const missing=classTemplates.filter(item=>!existing.has(item.code.toUpperCase())&&!existing.has(item.name.toUpperCase()));
  if(missing.length===0){
   setError(null);
   window.alert('All standard classes for this school type already exist.');
   return;
  }
  if(!window.confirm('Create '+missing.length+' missing standard classes for '+selectedSchool.name+'? Existing classes will be kept.'))return;
  setSaving(true);setError(null);
  try{
   for(const item of missing){
    await api.post('/api/v1/classes',{name:item.name,code:item.code,level:item.level,description:item.description},{school_id:selectedSchool.id});
   }
   await load();
   setTab('classes');
  }catch(e){
   setError(e instanceof Error?e.message:'Could not generate standard classes. Any classes already created were kept; retry to add the remaining ones.');
   await load();
  }finally{setSaving(false);}
 }

 async function addRecommendedSubjects(){
  if(!selectedSchool)return;
  const templates=getSubjectTemplates(selectedSchool.institution_type,selectedSchool.country_code);
  if(templates.length===0){setError('Choose a supported school type in School Configuration before adding recommended subjects.');return;}
  const existing=new Set(subjects.flatMap(item=>[item.code.trim().toUpperCase(),item.name.trim().toUpperCase()]));
  const missing=templates.filter(item=>{
   const code=item.code.toUpperCase(),name=item.name.toUpperCase();
   if(existing.has(code)||existing.has(name))return false;
   existing.add(code);existing.add(name);return true;
  });
  if(missing.length===0){setError(null);window.alert('All recommended subjects already exist for this school. No duplicates were created.');return;}
  if(!window.confirm('Add '+missing.length+' recommended subjects to '+selectedSchool.name+'? Existing subjects will be kept. Review the list against the school\'s approved curriculum afterwards.'))return;
  setSaving(true);setError(null);
  try{
   for(const item of missing) await api.post('/api/v1/subjects',{name:item.name,code:item.code,description:item.description},{school_id:selectedSchool.id});
   await load();setTab('subjects');
   window.alert('Added '+missing.length+' recommended subjects. Review them against the school\'s approved curriculum before assigning them to classes.');
  }catch(e){setError(e instanceof Error?e.message:'Could not finish adding recommended subjects. Subjects already created were kept; retry to add any remaining subjects.');await load();}
  finally{setSaving(false);}
 }

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
  {selectedSchool&&<Card><div className="flex flex-wrap items-center justify-between gap-3 p-4"><div><p className="font-medium text-slate-900">Standard class structure</p><p className="mt-1 text-sm text-slate-600">{selectedSchool.institution_type==='primary'?'Primary: ECG and Grade 1–7':selectedSchool.institution_type==='secondary'?'Secondary: Form 1–4':selectedSchool.institution_type==='high_school'?'High school: Form 1–6':selectedSchool.institution_type==='combined'?'Combined: ECG, Grade 1–7 and Form 1–6':selectedSchool.institution_type==='early_childhood'?'Early childhood: ECG':'Choose the school type in Schools to enable the recommended class structure.'}</p></div><Button variant="secondary" disabled={saving||classTemplates.length===0} onClick={()=>void applyClassTemplate()}>{saving?'Applying…':'Add missing standard classes'}</Button></div></Card>}
  {!selectedSchool&&<Card><EmptyState title="No school selected" hint="Choose a school from the selector in the header."/></Card>}
  {selectedSchool&&error&&<ErrorBanner message={error} onRetry={load}/>}
  {selectedSchool&&loading&&<Spinner label="Loading academic setup…"/>}
  {selectedSchool&&!loading&&tab==='years'&&<Card>{years.length===0?<EmptyState title="No academic years yet" hint="Create an academic year before adding terms and enrollments."/>:<Table headers={['Name','Start','End','Current','Status','Actions']}>{years.map(x=><tr key={x.id}><Td className="font-medium">{x.name}</Td><Td>{x.start_date}</Td><Td>{x.end_date}</Td><Td>{x.is_current?<Badge tone="green">Current</Badge>:'—'}</Td><Td><Badge tone={x.is_active?'green':'slate'}>{x.is_active?'Active':'Inactive'}</Badge></Td><Td><div className="flex gap-2"><Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={()=>editYear(x)}>Edit</Button>{x.is_active&&<Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void deactivate('years',x.id,x.name)}>Deactivate</Button>}</div></Td></tr>)}</Table>}</Card>}
  {selectedSchool&&!loading&&tab==='terms'&&<div className="space-y-3"><Card><div className="p-4"><Field label="Academic year" required><Select value={yearId} onChange={e=>setYearId(e.target.value)}><option value="">Select academic year…</option>{activeYears.map(x=><option key={x.id} value={x.id}>{x.name}{x.is_current?' (Current)':''}</option>)}</Select></Field></div></Card><Card>{rows.length===0?<EmptyState title="No terms for this year" hint="Select an academic year and create its first term."/>:<Table headers={['Term','Number','Start','End','Current','Status','Actions']}>{rows.map(x=><tr key={x.id}><Td className="font-medium">{x.name}</Td><Td>{x.term_number}</Td><Td>{x.start_date}</Td><Td>{x.end_date}</Td><Td>{x.is_current?<Badge tone="green">Current</Badge>:'—'}</Td><Td><Badge tone={x.is_active?'green':'slate'}>{x.is_active?'Active':'Inactive'}</Badge></Td><Td><div className="flex gap-2"><Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={()=>editTerm(x)}>Edit</Button>{x.is_active&&<Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void deactivate('terms',x.id,x.name)}>Deactivate</Button>}</div></Td></tr>)}</Table>}</Card></div>}
  {selectedSchool&&!loading&&tab==='classes'&&<Card>{classes.length===0?<EmptyState title="No classes yet" hint="Add classes such as Form 1, Form 2 or Grade 7."/>:<Table headers={['Name','Code','Level','Stream','Status','Actions']}>{classes.map(x=><tr key={x.id}><Td className="font-medium">{x.name}</Td><Td>{x.code}</Td><Td>{x.level??'—'}</Td><Td>{x.stream||'—'}</Td><Td><Badge tone={x.is_active?'green':'slate'}>{x.is_active?'Active':'Inactive'}</Badge></Td><Td><div className="flex gap-2"><Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={()=>editClass(x)}>Edit</Button>{x.is_active&&<Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void deactivate('classes',x.id,x.name)}>Deactivate</Button>}</div></Td></tr>)}</Table>}</Card>}
  {selectedSchool&&!loading&&tab==='class-subjects'&&<div className="space-y-3"><Card><div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-3"><Field label="Class" required><Select value={selectedClassId} onChange={e=>setSelectedClassId(e.target.value)}><option value="">Select class…</option>{classes.filter(x=>x.is_active).map(x=><option key={x.id} value={x.id}>{x.name} ({x.code})</option>)}</Select></Field><Field label="Subject to assign" required><Select value={selectedSubjectId} onChange={e=>setSelectedSubjectId(e.target.value)}><option value="">Select subject…</option>{subjects.filter(x=>x.is_active&&!assignments.some(a=>a.subject_id===x.id)).map(x=><option key={x.id} value={x.id}>{x.name} ({x.code})</option>)}</Select></Field><div className="flex items-end"><Button disabled={!selectedClassId||!selectedSubjectId||assigning} onClick={()=>void assignSubject()}>{assigning?'Assigning…':'Assign subject'}</Button></div></div></Card><Card>{!selectedClassId?<EmptyState title="No classes available" hint="Create a class before assigning subjects."/>:assignments.length===0?<EmptyState title="No subjects assigned" hint="Choose a subject above and assign it to this class."/>:<Table headers={['Subject','Code','Actions']}>{assignments.map(x=><tr key={x.id}><Td className="font-medium">{x.subject_name||subjects.find(s=>s.id===x.subject_id)?.name||'Subject'}</Td><Td>{x.subject_code||subjects.find(s=>s.id===x.subject_id)?.code||'—'}</Td><Td><Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void removeAssignment(x)}>Remove</Button></Td></tr>)}</Table>}</Card></div>}
  {selectedSchool&&!loading&&tab==='subjects'&&<Card><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4"><div><p className="font-medium text-slate-900">Subjects for {selectedSchool.name}</p><p className="mt-1 text-sm text-slate-600">Recommended starting list for this school type. Confirm subjects against the approved curriculum before use.</p></div><Button variant="secondary" disabled={saving} onClick={()=>void addRecommendedSubjects()}>{saving?'Adding subjects…':'Add recommended subjects'}</Button></div>{subjects.length===0?<EmptyState title="No subjects yet" hint="Add a recommended starter list, or use + Add Subject to create a subject manually."/>:<Table headers={['Subject','Code','Description','Status','Actions']}>{subjects.map(x=><tr key={x.id}><Td className="font-medium">{x.name}</Td><Td>{x.code}</Td><Td>{x.description||'—'}</Td><Td><Badge tone={x.is_active?'green':'slate'}>{x.is_active?'Active':'Inactive'}</Badge></Td><Td><div className="flex gap-2"><Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={()=>editSubject(x)}>Edit</Button>{x.is_active&&<Button variant="danger" className="!px-2 !py-1 text-xs" onClick={()=>void deactivate('subjects',x.id,x.name)}>Deactivate</Button>}</div></Td></tr>)}</Table>}</Card>}
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
