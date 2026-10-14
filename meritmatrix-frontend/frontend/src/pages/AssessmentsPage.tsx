import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { AcademicYearResponse, ClassResponse, ClassSubjectResponse, TermResponse } from '../types';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

type Assessment = {
  id: string; title: string; class_subject_id: string; term_id: string;
  assessment_type: string; assessment_date: string | null; max_score: number;
  weight_percent: number; is_published: boolean; class_name: string; class_code: string;
  subject_name: string; subject_code: string; term_name: string;
};
type RosterRow = { enrollment_id: string; student_id: string; student_number: string; student_name: string; score: number | null; remarks: string | null };
type ResultRow = { student_id: string; student_number: string; student_name: string; subject_name: string; term_name: string; weighted_percentage: number | null; marks_recorded: number; assessments_count: number };

export default function AssessmentsPage() {
  const { selectedSchool } = useSchool();
  const [classes, setClasses] = useState<ClassResponse[]>([]);
  const [years, setYears] = useState<AcademicYearResponse[]>([]);
  const [terms, setTerms] = useState<TermResponse[]>([]);
  const [classSubjects, setClassSubjects] = useState<ClassSubjectResponse[]>([]);
  const [classId, setClassId] = useState('');
  const [termId, setTermId] = useState('');
  const [classSubjectId, setClassSubjectId] = useState('');
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [assessmentId, setAssessmentId] = useState('');
  const [roster, setRoster] = useState<RosterRow[]>([]);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [title, setTitle] = useState('');
  const [type, setType] = useState('test');
  const [date, setDate] = useState('');
  const [maxScore, setMaxScore] = useState('100');
  const [weight, setWeight] = useState('100');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');

  const loadSetup = useCallback(async () => {
    if (!selectedSchool) { setClasses([]); setYears([]); setTerms([]); setClassSubjects([]); return; }
    setLoading(true); setError(null);
    try {
      const [classRows, yearRows] = await Promise.all([
        api.get<ClassResponse[]>('/api/v1/classes', { school_id: selectedSchool.id }),
        api.get<AcademicYearResponse[]>('/api/v1/academic-years', { school_id: selectedSchool.id }),
      ]);
      setClasses(classRows.filter(x => x.is_active));
      setYears(yearRows);
      const termGroups = await Promise.all(yearRows.map(y => api.get<TermResponse[]>('/api/v1/terms', { academic_year_id: y.id }).catch(() => [] as TermResponse[])));
      const allTerms = termGroups.flat().filter(t => t.is_active);
      setTerms(allTerms);
      setClassId(current => classRows.some(x => x.id === current && x.is_active) ? current : classRows.find(x => x.is_active)?.id ?? '');
      setTermId(current => allTerms.some(x => x.id === current) ? current : allTerms.find(x => x.is_current)?.id ?? allTerms[0]?.id ?? '');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load academic setup.'); }
    finally { setLoading(false); }
  }, [selectedSchool]);

  useEffect(() => { void loadSetup(); }, [loadSetup]);

  const loadClassSubjects = useCallback(async () => {
    if (!classId) { setClassSubjects([]); setClassSubjectId(''); return; }
    try {
      const rows = await api.get<ClassSubjectResponse[]>('/api/v1/class-subjects', { class_id: classId });
      setClassSubjects(rows);
      setClassSubjectId(current => rows.some(x => x.id === current) ? current : rows[0]?.id ?? '');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load class subjects.'); }
  }, [classId]);
  useEffect(() => { void loadClassSubjects(); }, [loadClassSubjects]);

  const loadAssessments = useCallback(async () => {
    if (!selectedSchool || !classId || !termId) { setAssessments([]); setAssessmentId(''); return; }
    try {
      const rows = await api.get<Assessment[]>('/api/v1/assessments', { school_id: selectedSchool.id, class_id: classId, term_id: termId });
      setAssessments(rows);
      setAssessmentId(current => rows.some(x => x.id === current) ? current : rows[0]?.id ?? '');
    } catch (e) { setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not load assessments.'); }
  }, [selectedSchool, classId, termId]);
  useEffect(() => { void loadAssessments(); }, [loadAssessments]);

  const loadRosterAndResults = useCallback(async () => {
    if (!selectedSchool || !classId || !termId) { setRoster([]); setResults([]); return; }
    try {
      const resultRows = await api.get<ResultRow[]>('/api/v1/results', { school_id: selectedSchool.id, class_id: classId, term_id: termId });
      setResults(resultRows);
      if (assessmentId) {
        const rosterRows = await api.get<RosterRow[]>('/api/v1/assessments/' + assessmentId + '/roster');
        setRoster(rosterRows);
      } else setRoster([]);
    } catch (e) { setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not load marks.'); }
  }, [selectedSchool, classId, termId, assessmentId]);
  useEffect(() => { void loadRosterAndResults(); }, [loadRosterAndResults]);

  async function createAssessment() {
    if (!selectedSchool || !classSubjectId || !termId || !title.trim()) { setError('Choose a class subject and term, and enter an assessment title.'); return; }
    setSaving(true); setError(null); setNotice('');
    try {
      const created = await api.post<Assessment>('/api/v1/assessments', {
        class_subject_id: classSubjectId, term_id: termId, title: title.trim(),
        assessment_type: type, assessment_date: date || null, max_score: Number(maxScore),
        weight_percent: Number(weight), is_published: false,
      }, { school_id: selectedSchool.id });
      setTitle(''); setAssessmentId(created.id);
      setNotice('Assessment created. Enter marks below, then publish when they are ready.');
      await loadAssessments();
      setAssessmentId(created.id);
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not create assessment.'); }
    finally { setSaving(false); }
  }

  function updateRow(enrollmentId: string, field: 'score' | 'remarks', value: string) {
    setRoster(rows => rows.map(row => row.enrollment_id !== enrollmentId ? row : {
      ...row, [field]: field === 'score' ? (value === '' ? null : Number(value)) : value,
    }));
  }

  async function saveMarks() {
    const assessment = assessments.find(x => x.id === assessmentId);
    if (!assessment || assessment.is_published) return;
    const marks = roster.filter(row => row.score !== null && Number.isFinite(row.score)).map(row => ({
      enrollment_id: row.enrollment_id, score: Number(row.score), remarks: row.remarks || null,
    }));
    if (!marks.length) { setError('Enter at least one mark before saving.'); return; }
    setSaving(true); setError(null); setNotice('');
    try {
      await api.put('/api/v1/assessments/' + assessmentId + '/marks', { marks });
      setNotice('Saved marks for ' + marks.length + ' student(s).');
      await loadRosterAndResults();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not save marks.'); }
    finally { setSaving(false); }
  }

  async function publishAssessment() {
    const assessment = assessments.find(x => x.id === assessmentId);
    if (!assessment || assessment.is_published) return;
    if (!window.confirm('Publish these results to linked guardians? Published marks are locked until an administrator unpublishes the assessment.')) return;
    setSaving(true); setError(null); setNotice('');
    try {
      await api.patch('/api/v1/assessments/' + assessmentId, { is_published: true });
      setNotice('Results published to the guardian portal.');
      await loadAssessments();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not publish results.'); }
    finally { setSaving(false); }
  }

  const selectedAssessment = assessments.find(x => x.id === assessmentId);
  if (!selectedSchool) return <div><PageHeader title="Assessments & Results" subtitle="Select a school to manage assessments."/><Card className="p-6">Choose a school from the selector above.</Card></div>;

  return <div className="space-y-5">
    <PageHeader title="Assessments & Results" subtitle={'Create assessments, enter marks and publish verified results for ' + selectedSchool.name + '.'} actions={<Button variant="secondary" onClick={() => { void loadSetup(); void loadAssessments(); void loadRosterAndResults(); }}>Refresh</Button>} />
    {error && <ErrorBanner message={error} onRetry={() => { void loadSetup(); void loadAssessments(); void loadRosterAndResults(); }} />}
    {notice && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    {loading ? <Card className="p-6"><Spinner label="Loading school academic structure…"/></Card> : <>
      <Card className="p-4">
        <h2 className="font-semibold text-slate-900">Assessment setup</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-sm font-medium text-slate-700">Class<select value={classId} onChange={e => setClassId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose class…</option>{classes.map(x => <option key={x.id} value={x.id}>{x.name} ({x.code})</option>)}</select></label>
          <label className="text-sm font-medium text-slate-700">Subject<select value={classSubjectId} onChange={e => setClassSubjectId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose subject…</option>{classSubjects.map(x => <option key={x.id} value={x.id}>{x.subject_name ?? x.subject_code ?? x.id}</option>)}</select></label>
          <label className="text-sm font-medium text-slate-700">Term<select value={termId} onChange={e => setTermId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose term…</option>{terms.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
          <label className="text-sm font-medium text-slate-700">Assessment type<select value={type} onChange={e => setType(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="test">Test</option><option value="exam">Exam</option><option value="assignment">Assignment</option><option value="project">Project</option><option value="practical">Practical</option><option value="oral">Oral</option></select></label>
          <label className="text-sm font-medium text-slate-700 sm:col-span-2">Assessment title<input value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Term 3 Mathematics Test" className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label>
          <label className="text-sm font-medium text-slate-700">Date<input type="date" value={date} onChange={e => setDate(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label>
          <label className="text-sm font-medium text-slate-700">Maximum score<input type="number" min="1" step="0.5" value={maxScore} onChange={e => setMaxScore(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label>
          <label className="text-sm font-medium text-slate-700">Weight (%)<input type="number" min="0.1" max="100" step="0.1" value={weight} onChange={e => setWeight(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label>
        </div>
        <div className="mt-4"><Button onClick={() => void createAssessment()} disabled={saving || !classSubjectId || !termId || !title.trim()}>{saving ? 'Saving…' : 'Create assessment'}</Button></div>
      </Card>

      <Card className="p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-64 flex-1"><label className="text-sm font-medium text-slate-700">Assessment to mark<select value={assessmentId} onChange={e => setAssessmentId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose assessment…</option>{assessments.map(x => <option key={x.id} value={x.id}>{x.subject_name} · {x.title}{x.is_published ? ' (Published)' : ''}</option>)}</select></label></div>
          {selectedAssessment && <div className="text-sm text-slate-500">Maximum: {selectedAssessment.max_score} · Weight: {selectedAssessment.weight_percent}%</div>}
        </div>
        {selectedAssessment && <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className={'rounded-full px-2.5 py-1 text-xs font-medium ' + (selectedAssessment.is_published ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700')}>{selectedAssessment.is_published ? 'Published' : 'Draft'}</span>
          {!selectedAssessment.is_published && <><Button variant="secondary" onClick={() => void saveMarks()} disabled={saving}>{saving ? 'Saving…' : 'Save marks'}</Button><Button onClick={() => void publishAssessment()} disabled={saving}>Publish results</Button></>}
        </div>}
        {!selectedAssessment ? <p className="mt-4 text-sm text-slate-500">Create or select an assessment to enter marks.</p> : roster.length === 0 ? <p className="mt-4 text-sm text-slate-500">No active students are enrolled in this class for the assessment term.</p> : <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200"><table className="min-w-full divide-y divide-slate-200 text-sm"><thead className="bg-slate-50"><tr><th className="px-3 py-3 text-left font-semibold text-slate-600">Student</th><th className="px-3 py-3 text-left font-semibold text-slate-600">Score / {selectedAssessment.max_score}</th><th className="px-3 py-3 text-left font-semibold text-slate-600">Teacher remarks</th></tr></thead><tbody className="divide-y divide-slate-100">{roster.map(row => <tr key={row.enrollment_id}><td className="px-3 py-3"><p className="font-medium text-slate-900">{row.student_name}</p><p className="text-xs text-slate-500">{row.student_number}</p></td><td className="px-3 py-3"><input aria-label={'Score for ' + row.student_name} type="number" min="0" max={selectedAssessment.max_score} step="0.1" disabled={selectedAssessment.is_published} value={row.score ?? ''} onChange={e => updateRow(row.enrollment_id, 'score', e.target.value)} className="w-32 rounded-md border border-slate-300 p-2 disabled:bg-slate-100"/></td><td className="px-3 py-3"><input aria-label={'Remarks for ' + row.student_name} disabled={selectedAssessment.is_published} value={row.remarks ?? ''} onChange={e => updateRow(row.enrollment_id, 'remarks', e.target.value)} placeholder="Optional feedback" className="w-full min-w-48 rounded-md border border-slate-300 p-2 disabled:bg-slate-100"/></td></tr>)}</tbody></table></div>}
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold text-slate-900">Published results summary</h2>
        {results.length === 0 ? <p className="mt-3 text-sm text-slate-500">No published marks for this class and term yet.</p> : <div className="mt-3 overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-sm"><thead className="bg-slate-50"><tr><th className="px-3 py-2 text-left font-semibold text-slate-600">Student</th><th className="px-3 py-2 text-left font-semibold text-slate-600">Subject</th><th className="px-3 py-2 text-left font-semibold text-slate-600">Term</th><th className="px-3 py-2 text-right font-semibold text-slate-600">Weighted average</th><th className="px-3 py-2 text-right font-semibold text-slate-600">Marks</th></tr></thead><tbody className="divide-y divide-slate-100">{results.map((row, i) => <tr key={row.student_id + row.subject_name + row.term_name + i}><td className="px-3 py-2"><p className="font-medium text-slate-900">{row.student_name}</p><p className="text-xs text-slate-500">{row.student_number}</p></td><td className="px-3 py-2">{row.subject_name}</td><td className="px-3 py-2">{row.term_name}</td><td className="px-3 py-2 text-right font-semibold">{row.weighted_percentage == null ? '—' : row.weighted_percentage + '%'}</td><td className="px-3 py-2 text-right">{row.marks_recorded}/{row.assessments_count}</td></tr>)}</tbody></table></div>}
      </Card>
    </>}
  </div>;
}
