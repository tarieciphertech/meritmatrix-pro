import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import { useAuth } from '../lib/auth';
import type { AcademicYearResponse, ClassResponse, ClassSubjectResponse, TermResponse } from '../types';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

type Assessment = {
  id: string; school_id: string; title: string; class_subject_id: string; term_id: string;
  assessment_type: string; assessment_date: string | null; max_score: number;
  weight_percent: number; is_published: boolean; marks_submitted: boolean; class_name: string; class_code: string;
  subject_name: string; subject_code: string; term_name: string;
};
type RosterRow = { enrollment_id: string; student_id: string; student_number: string; student_name: string; score: number | null; remarks: string | null };
type ResultRow = { student_id: string; student_number: string; student_name: string; subject_name: string; term_name: string; weighted_percentage: number | null; grade_label?: string | null; grade_comment?: string | null; marks_recorded: number; assessments_count: number };
type GradeBand = { id?: string; grade_label: string; min_percentage: number; max_percentage: number; comment: string; display_order: number; is_active: boolean };

export default function AssessmentsPage() {
  const { selectedSchool } = useSchool();
  const { hasRole } = useAuth();
  const canManageSchoolGrading = hasRole('SUPER_ADMIN') || hasRole('SCHOOL_ADMIN');
  const [classes, setClasses] = useState<ClassResponse[]>([]);
  const [terms, setTerms] = useState<TermResponse[]>([]);
  const [classSubjects, setClassSubjects] = useState<ClassSubjectResponse[]>([]);
  const [classId, setClassId] = useState('');
  const [termId, setTermId] = useState('');
  const [classSubjectId, setClassSubjectId] = useState('');
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [assessmentId, setAssessmentId] = useState('');
  const [roster, setRoster] = useState<RosterRow[]>([]);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [gradeBands, setGradeBands] = useState<GradeBand[]>([]);
  const [title, setTitle] = useState('');
  const [type, setType] = useState('test');
  const [date, setDate] = useState('');
  const [maxScore, setMaxScore] = useState('100');
  const [weight, setWeight] = useState('100');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const activeSchoolIdRef = useRef<string | null>(selectedSchool?.id ?? null);
  const activeClassIdRef = useRef(classId);
  const activeTermIdRef = useRef(termId);
  const activeAssessmentIdRef = useRef(assessmentId);
  activeClassIdRef.current = classId;
  activeTermIdRef.current = termId;
  activeAssessmentIdRef.current = assessmentId;

  // Clear all school-scoped academic data immediately on school changes. The
  // request guards below also prevent a slower previous-school request from
  // repopulating this screen after the user has switched schools.
  useEffect(() => {
    activeSchoolIdRef.current = selectedSchool?.id ?? null;
    setClasses([]); setTerms([]); setClassSubjects([]);
    setClassId(''); setTermId(''); setClassSubjectId('');
    setAssessments([]); setAssessmentId(''); setRoster([]); setResults([]);
    setGradeBands([]); setTitle(''); setError(null); setNotice('');
  }, [selectedSchool?.id]);

  const loadSetup = useCallback(async () => {
    if (!selectedSchool) {
      setClasses([]); setTerms([]); setClassSubjects([]); setAssessments([]);
      setClassId(''); setTermId(''); setClassSubjectId(''); setAssessmentId('');
      setRoster([]); setResults([]); setGradeBands([]); setLoading(false);
      return;
    }
    const requestSchoolId = selectedSchool.id;
    setLoading(true); setError(null);
    try {
      const [classRows, yearRows, bandRows] = await Promise.all([
        api.get<ClassResponse[]>('/api/v1/classes', { school_id: selectedSchool.id }),
        api.get<AcademicYearResponse[]>('/api/v1/academic-years', { school_id: selectedSchool.id }),
        api.get<GradeBand[]>('/api/v1/grading-scales', { school_id: selectedSchool.id }),
      ]);
      if (activeSchoolIdRef.current !== requestSchoolId) return;
      setGradeBands(bandRows.map(b => ({ ...b, comment: b.comment ?? '' })));
      setClasses(classRows.filter(x => x.is_active));
      const termGroups = await Promise.all(yearRows.map(y => api.get<TermResponse[]>('/api/v1/terms', { academic_year_id: y.id }).catch(() => [] as TermResponse[])));
      if (activeSchoolIdRef.current !== requestSchoolId) return;
      const allTerms = termGroups.flat().filter(t => t.is_active);
      setTerms(allTerms);
      setClassId(current => classRows.some(x => x.id === current && x.is_active) ? current : classRows.find(x => x.is_active)?.id ?? '');
      setTermId(current => allTerms.some(x => x.id === current) ? current : allTerms.find(x => x.is_current)?.id ?? allTerms[0]?.id ?? '');
    } catch (e) {
      if (activeSchoolIdRef.current === requestSchoolId) {
        setClasses([]); setTerms([]); setClassSubjects([]); setGradeBands([]);
        setError(e instanceof Error ? e.message : 'Could not load academic setup.');
      }
    } finally {
      if (activeSchoolIdRef.current === requestSchoolId) setLoading(false);
    }
  }, [selectedSchool]);

  useEffect(() => { void loadSetup(); }, [loadSetup]);

  const loadClassSubjects = useCallback(async () => {
    if (
      !selectedSchool || !classId ||
      !classes.some(clazz => clazz.id === classId && clazz.school_id === selectedSchool.id)
    ) {
      setClassSubjects([]); setClassSubjectId(''); return;
    }
    const requestSchoolId = selectedSchool.id;
    const requestClassId = classId;
    try {
      const rows = await api.get<ClassSubjectResponse[]>('/api/v1/class-subjects', { class_id: requestClassId });
      if (activeSchoolIdRef.current !== requestSchoolId || activeClassIdRef.current !== requestClassId) return;
      setClassSubjects(rows);
      setClassSubjectId(current => rows.some(x => x.id === current) ? current : rows[0]?.id ?? '');
    } catch (e) {
      if (activeSchoolIdRef.current === requestSchoolId) {
        setClassSubjects([]);
        setError(e instanceof Error ? e.message : 'Could not load class subjects.');
      }
    }
  }, [selectedSchool, classes, classId]);
  useEffect(() => { void loadClassSubjects(); }, [loadClassSubjects]);

  const loadAssessments = useCallback(async () => {
    if (!selectedSchool || !classId || !termId) { setAssessments([]); setAssessmentId(''); return; }
    const requestSchoolId = selectedSchool.id;
    const requestClassId = classId;
    const requestTermId = termId;
    try {
      const rows = await api.get<Assessment[]>('/api/v1/assessments', { school_id: requestSchoolId, class_id: requestClassId, term_id: requestTermId });
      if (activeSchoolIdRef.current !== requestSchoolId || activeClassIdRef.current !== requestClassId || activeTermIdRef.current !== requestTermId) return;
      setAssessments(rows);
      setAssessmentId(current => rows.some(x => x.id === current) ? current : rows[0]?.id ?? '');
    } catch (e) {
      if (activeSchoolIdRef.current === requestSchoolId) {
        setAssessments([]); setAssessmentId('');
        setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not load assessments.');
      }
    }
  }, [selectedSchool, classId, termId]);
  useEffect(() => { void loadAssessments(); }, [loadAssessments]);

  const loadRosterAndResults = useCallback(async () => {
    if (!selectedSchool || !classId || !termId) { setRoster([]); setResults([]); return; }
    const requestSchoolId = selectedSchool.id;
    const requestClassId = classId;
    const requestTermId = termId;
    const requestAssessmentId = assessmentId;
    try {
      const resultRows = await api.get<ResultRow[]>('/api/v1/results', { school_id: requestSchoolId, class_id: requestClassId, term_id: requestTermId });
      if (activeSchoolIdRef.current !== requestSchoolId || activeClassIdRef.current !== requestClassId || activeTermIdRef.current !== requestTermId) return;
      setResults(resultRows);
      const selectedAssessment = assessments.find(item => item.id === requestAssessmentId && item.school_id === requestSchoolId);
      if (selectedAssessment && activeAssessmentIdRef.current === requestAssessmentId) {
        const rosterRows = await api.get<RosterRow[]>('/api/v1/assessments/' + selectedAssessment.id + '/roster');
        if (activeSchoolIdRef.current !== requestSchoolId || activeClassIdRef.current !== requestClassId || activeTermIdRef.current !== requestTermId || activeAssessmentIdRef.current !== requestAssessmentId) return;
        setRoster(rosterRows);
      } else setRoster([]);
    } catch (e) {
      if (activeSchoolIdRef.current === requestSchoolId) {
        setRoster([]); setResults([]);
        setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not load marks.');
      }
    }
  }, [selectedSchool, classId, termId, assessmentId, assessments]);
  useEffect(() => { void loadRosterAndResults(); }, [loadRosterAndResults]);

  function updateBand(index: number, field: keyof GradeBand, value: string | number | boolean) {
    setGradeBands(current => current.map((band, i) => i !== index ? band : { ...band, [field]: value }));
  }

  async function saveGradingScale() {
    if (!selectedSchool) return;
    if (!canManageSchoolGrading) {
      setError('Only a school administrator can manage the school grading scale.');
      return;
    }
    if (gradeBands.some(band => !band.grade_label.trim())) {
      setError('Every grading band needs a grade label before the scale can be saved.');
      return;
    }
    if (gradeBands.some(band => band.min_percentage < 0 || band.max_percentage > 100)) {
      setError('Grading percentages must stay between 0 and 100.');
      return;
    }
    const orderedBands = gradeBands.filter(band => band.is_active).sort((a, b) => a.min_percentage - b.min_percentage);
    if (orderedBands.some(band => band.min_percentage > band.max_percentage)) {
      setError('Each active grading band minimum must be less than or equal to its maximum.');
      return;
    }
    if (orderedBands.some((band, index) => index > 0 && band.min_percentage <= orderedBands[index - 1].max_percentage)) {
      setError('Active grading bands must not overlap. Adjust the ranges before saving.');
      return;
    }
    setSaving(true); setError(null); setNotice('');
    try {
      const saved = await api.put<GradeBand[]>('/api/v1/grading-scales', {
        bands: gradeBands.map((band, index) => ({
          grade_label: band.grade_label.trim(),
          min_percentage: Number(band.min_percentage),
          max_percentage: Number(band.max_percentage),
          comment: band.comment.trim() || null,
          display_order: index,
          is_active: band.is_active,
        })),
      }, { school_id: selectedSchool.id });
      setGradeBands(saved.map(b => ({ ...b, comment: b.comment ?? '' })));
      setNotice('School grading scale saved. Grades are now calculated for matching published results.');
      await loadRosterAndResults();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not save grading scale.'); }
    finally { setSaving(false); }
  }

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
      setNotice('Assessment created. Enter marks for every active student, then submit them for administrator verification.');
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

  async function submitMarksForReview() {
    const assessment = assessments.find(x => x.id === assessmentId);
    if (!assessment || assessment.is_published || assessment.marks_submitted) return;
    if (roster.length === 0 || roster.some(row => row.score === null || !Number.isFinite(Number(row.score)))) {
      setError('Enter a score for every active student before submitting for verification.');
      return;
    }
    if (!window.confirm('Save the current marks and submit them for school administrator verification? The marks will be locked until an administrator returns them to draft.')) return;
    setSaving(true); setError(null); setNotice('');
    try {
      const marks = roster.map(row => ({
        enrollment_id: row.enrollment_id,
        score: Number(row.score),
        remarks: row.remarks || null,
      }));
      await api.put('/api/v1/assessments/' + assessmentId + '/marks', { marks });
      const updated = await api.post<Assessment>('/api/v1/assessments/' + assessmentId + '/submit-for-review', {});
      setAssessments(current => current.map(item => item.id === updated.id ? updated : item));
      setNotice('Current marks saved and submitted for verification. They will not be visible to guardians until an administrator publishes the verified results.');
      await loadRosterAndResults();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not submit marks for verification.'); }
    finally { setSaving(false); }
  }

  async function returnAssessmentToDraft() {
    const assessment = assessments.find(x => x.id === assessmentId);
    if (!assessment || assessment.is_published || !assessment.marks_submitted || !canManageSchoolGrading) return;
    if (!window.confirm('Return these marks to draft so the teacher can correct them?')) return;
    setSaving(true); setError(null); setNotice('');
    try {
      const updated = await api.post<Assessment>('/api/v1/assessments/' + assessmentId + '/return-to-draft', {});
      setAssessments(current => current.map(item => item.id === updated.id ? updated : item));
      setNotice('Assessment returned to draft. The teacher can edit the marks and submit them again.');
      await loadRosterAndResults();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not return marks to draft.'); }
    finally { setSaving(false); }
  }

  async function publishAssessment() {
    const assessment = assessments.find(x => x.id === assessmentId);
    if (!assessment || assessment.is_published || !assessment.marks_submitted || !canManageSchoolGrading) return;
    if (!window.confirm('Publish these verified results to linked guardians? Published marks will become visible to guardians.')) return;
    setSaving(true); setError(null); setNotice('');
    try {
      await api.patch('/api/v1/assessments/' + assessmentId, { is_published: true });
      setNotice('Verified results published to the guardian portal.');
      await loadAssessments();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not publish results.'); }
    finally { setSaving(false); }
  }

  async function unpublishAssessment() {
    const assessment = assessments.find(x => x.id === assessmentId);
    if (!assessment || !assessment.is_published || !canManageSchoolGrading) return;
    if (!window.confirm('Unpublish these results and return the assessment to draft for corrections? Guardians will no longer see these results until they are verified and published again.')) return;
    setSaving(true); setError(null); setNotice('');
    try {
      const updated = await api.patch<Assessment>('/api/v1/assessments/' + assessmentId, { is_published: false });
      setAssessments(current => current.map(item => item.id === updated.id ? updated : item));
      setNotice('Results unpublished and returned to draft. Correct the marks, then submit them for verification again.');
      await loadAssessments();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not unpublish results.'); }
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
          <div className="min-w-64 flex-1"><label className="text-sm font-medium text-slate-700">Assessment to mark<select value={assessmentId} onChange={e => setAssessmentId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose assessment…</option>{assessments.map(x => <option key={x.id} value={x.id}>{x.subject_name} · {x.title}{x.is_published ? ' (Published)' : x.marks_submitted ? ' (Submitted for verification)' : ' (Draft)'}</option>)}</select></label></div>
          {selectedAssessment && <div className="text-sm text-slate-500">Maximum: {selectedAssessment.max_score} · Weight: {selectedAssessment.weight_percent}%</div>}
        </div>
        {selectedAssessment && <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className={'rounded-full px-2.5 py-1 text-xs font-medium ' + (selectedAssessment.is_published ? 'bg-emerald-50 text-emerald-700' : selectedAssessment.marks_submitted ? 'bg-sky-50 text-sky-700' : 'bg-amber-50 text-amber-700')}>{selectedAssessment.is_published ? 'Published' : selectedAssessment.marks_submitted ? 'Submitted for verification' : 'Draft'}</span>
          {!selectedAssessment.is_published && !selectedAssessment.marks_submitted && <><Button variant="secondary" onClick={() => void saveMarks()} disabled={saving}>{saving ? 'Saving…' : 'Save marks'}</Button><Button onClick={() => void submitMarksForReview()} disabled={saving || roster.length === 0 || roster.some(row => row.score === null || !Number.isFinite(Number(row.score)))}>{saving ? 'Submitting…' : 'Submit for verification'}</Button></>}
          {!selectedAssessment.is_published && selectedAssessment.marks_submitted && canManageSchoolGrading && <><Button onClick={() => void publishAssessment()} disabled={saving}>{saving ? 'Publishing…' : 'Publish verified results'}</Button><Button variant="secondary" onClick={() => void returnAssessmentToDraft()} disabled={saving}>Return to draft</Button></>}
          {selectedAssessment.is_published && canManageSchoolGrading && <Button variant="secondary" onClick={() => void unpublishAssessment()} disabled={saving}>{saving ? 'Unpublishing…' : 'Unpublish for corrections'}</Button>}
        </div>}
        {selectedAssessment?.marks_submitted && !selectedAssessment.is_published && !canManageSchoolGrading && <p className="mt-3 rounded-md bg-sky-50 p-3 text-sm text-sky-800">Marks are submitted and locked for review. A school administrator must verify and publish them before guardians can see the results.</p>}
        {!selectedAssessment ? <p className="mt-4 text-sm text-slate-500">Create or select an assessment to enter marks.</p> : roster.length === 0 ? <p className="mt-4 text-sm text-slate-500">No active students are enrolled in this class for the assessment term.</p> : <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200"><table className="min-w-full divide-y divide-slate-200 text-sm"><thead className="bg-slate-50"><tr><th className="px-3 py-3 text-left font-semibold text-slate-600">Student</th><th className="px-3 py-3 text-left font-semibold text-slate-600">Score / {selectedAssessment.max_score}</th><th className="px-3 py-3 text-left font-semibold text-slate-600">Teacher remarks</th></tr></thead><tbody className="divide-y divide-slate-100">{roster.map(row => <tr key={row.enrollment_id}><td className="px-3 py-3"><p className="font-medium text-slate-900">{row.student_name}</p><p className="text-xs text-slate-500">{row.student_number}</p></td><td className="px-3 py-3"><input aria-label={'Score for ' + row.student_name} type="number" min="0" max={selectedAssessment.max_score} step="0.1" disabled={selectedAssessment.is_published || selectedAssessment.marks_submitted} value={row.score ?? ''} onChange={e => updateRow(row.enrollment_id, 'score', e.target.value)} className="w-32 rounded-md border border-slate-300 p-2 disabled:bg-slate-100"/></td><td className="px-3 py-3"><input aria-label={'Remarks for ' + row.student_name} disabled={selectedAssessment.is_published || selectedAssessment.marks_submitted} value={row.remarks ?? ''} onChange={e => updateRow(row.enrollment_id, 'remarks', e.target.value)} placeholder="Optional feedback" className="w-full min-w-48 rounded-md border border-slate-300 p-2 disabled:bg-slate-100"/></td></tr>)}</tbody></table></div>}
      </Card>

      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="font-semibold text-slate-900">School grading scale</h2><p className="mt-1 text-sm text-slate-500">School-approved grade labels and percentage ranges. Active ranges must not overlap.</p></div>
          {canManageSchoolGrading && <div className="flex gap-2"><Button variant="secondary" onClick={() => setGradeBands(current => [...current, { grade_label: '', min_percentage: 0, max_percentage: 0, comment: '', display_order: current.length, is_active: true }])}>Add band</Button><Button onClick={() => void saveGradingScale()} disabled={saving || gradeBands.length===0}>{saving ? 'Saving…' : 'Save grading scale'}</Button></div>}
        </div>
        {!canManageSchoolGrading ? <div className="mt-3 rounded-md bg-slate-50 p-3 text-sm text-slate-600">
          <p>Only a school administrator can configure or change the school-wide grading scale.</p>
          {gradeBands.length === 0 ? <p className="mt-1">No grading bands are configured yet. Ask the school administrator to enter the approved ranges.</p> : <ul className="mt-2 space-y-1">{gradeBands.filter(b => b.is_active).map((band, index) => <li key={band.id ?? index}>{band.grade_label}: {band.min_percentage}%–{band.max_percentage}%{band.comment ? ' — ' + band.comment : ''}</li>)}</ul>}
        </div> : <>
{gradeBands.length===0 ? <p className="mt-3 rounded-md bg-slate-50 p-3 text-sm text-slate-500">No grade bands configured. Add the ranges approved by this school or its education authority.</p> : <div className="mt-3 space-y-2">{gradeBands.map((band,index)=><div key={band.id ?? 'new-'+index} className="grid gap-2 rounded-lg border border-slate-200 p-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-xs font-medium text-slate-600">Grade label<input value={band.grade_label} onChange={e=>updateBand(index,'grade_label',e.target.value)} placeholder="A, B, Merit…" className="mt-1 block w-full rounded-md border border-slate-300 p-2 text-sm"/></label>
          <label className="text-xs font-medium text-slate-600">Minimum %<input type="number" min="0" max="100" step="0.1" value={band.min_percentage} onChange={e=>updateBand(index,'min_percentage',Number(e.target.value))} className="mt-1 block w-full rounded-md border border-slate-300 p-2 text-sm"/></label>
          <label className="text-xs font-medium text-slate-600">Maximum %<input type="number" min="0" max="100" step="0.1" value={band.max_percentage} onChange={e=>updateBand(index,'max_percentage',Number(e.target.value))} className="mt-1 block w-full rounded-md border border-slate-300 p-2 text-sm"/></label>
          <label className="text-xs font-medium text-slate-600">Comment<input value={band.comment} onChange={e=>updateBand(index,'comment',e.target.value)} placeholder="Excellent, Good…" className="mt-1 block w-full rounded-md border border-slate-300 p-2 text-sm"/></label>
          <div className="flex items-end justify-between gap-2"><label className="flex items-center gap-2 pb-2 text-sm text-slate-600"><input type="checkbox" checked={band.is_active} onChange={e=>updateBand(index,'is_active',e.target.checked)}/>Active</label><Button variant="secondary" onClick={()=>setGradeBands(current=>current.filter((_,i)=>i!==index))}>Remove</Button></div>
        </div>)}</div>}

        </>}
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold text-slate-900">Published results summary</h2>
        {results.length === 0 ? <p className="mt-3 text-sm text-slate-500">No published marks for this class and term yet.</p> : <div className="mt-3 overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-sm"><thead className="bg-slate-50"><tr><th className="px-3 py-2 text-left font-semibold text-slate-600">Student</th><th className="px-3 py-2 text-left font-semibold text-slate-600">Subject</th><th className="px-3 py-2 text-left font-semibold text-slate-600">Term</th><th className="px-3 py-2 text-right font-semibold text-slate-600">Weighted average</th><th className="px-3 py-2 text-right font-semibold text-slate-600">Grade</th><th className="px-3 py-2 text-right font-semibold text-slate-600">Marks</th></tr></thead><tbody className="divide-y divide-slate-100">{results.map((row, i) => <tr key={row.student_id + row.subject_name + row.term_name + i}><td className="px-3 py-2"><p className="font-medium text-slate-900">{row.student_name}</p><p className="text-xs text-slate-500">{row.student_number}</p></td><td className="px-3 py-2">{row.subject_name}</td><td className="px-3 py-2">{row.term_name}</td><td className="px-3 py-2 text-right font-semibold">{row.weighted_percentage == null ? '—' : row.weighted_percentage + '%'}</td><td className="px-3 py-2 text-right">{row.grade_label ?? '—'}</td><td className="px-3 py-2 text-right">{row.marks_recorded}/{row.assessments_count}</td></tr>)}</tbody></table></div>}
      </Card>
    </>}
  </div>;
}
