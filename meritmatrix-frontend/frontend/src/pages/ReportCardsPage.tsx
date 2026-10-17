import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { AcademicYearResponse, StudentResponse, TermResponse } from '../types';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

type ResultRow = {
  student_id: string; student_number: string; student_name: string; class_id: string;
  class_name: string; subject_id: string; subject_name: string; term_id: string;
  term_name: string; assessments: { assessment_id: string; title: string; type: string; score: number; max_score: number; percentage: number; remarks?: string | null; date?: string | null }[];
  weighted_percentage: number | null; grade_label?: string | null; grade_comment?: string | null; marks_recorded: number; assessments_count: number;
};

export default function ReportCardsPage() {
  const { selectedSchool } = useSchool();
  const [students, setStudents] = useState<StudentResponse[]>([]);
  const [terms, setTerms] = useState<TermResponse[]>([]);
  const [studentId, setStudentId] = useState('');
  const [termId, setTermId] = useState('');
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSetup = useCallback(async () => {
    if (!selectedSchool) { setStudents([]); setTerms([]); setRows([]); setStudentId(''); setTermId(''); return; }
    // Clear the prior school's report-card data before loading the new school.
    setStudents([]); setTerms([]); setRows([]); setStudentId(''); setTermId('');
    setLoading(true); setError(null);
    try {
      const [studentRows, years] = await Promise.all([
        api.get<StudentResponse[]>('/api/v1/students', { school_id: selectedSchool.id }),
        api.get<AcademicYearResponse[]>('/api/v1/academic-years', { school_id: selectedSchool.id }),
      ]);
      setStudents(studentRows.filter(s => s.is_active));
      setStudentId(current => studentRows.some(s => s.id === current && s.is_active) ? current : studentRows.find(s => s.is_active)?.id ?? '');
      const termGroups = await Promise.all(years.map(y => api.get<TermResponse[]>('/api/v1/terms', { academic_year_id: y.id }).catch(() => [] as TermResponse[])));
      const termRows = termGroups.flat().filter(t => t.is_active);
      setTerms(termRows);
      setTermId(current => termRows.some(t => t.id === current) ? current : termRows.find(t => t.is_current)?.id ?? termRows[0]?.id ?? '');
    } catch (e) {
      setStudents([]); setTerms([]); setRows([]); setStudentId(''); setTermId('');
      setError(e instanceof Error ? e.message : 'Could not load report-card setup.');
    }
    finally { setLoading(false); }
  }, [selectedSchool]);
  useEffect(() => { void loadSetup(); }, [loadSetup]);

  const loadResults = useCallback(async () => {
    if (!selectedSchool || !studentId || !termId) { setRows([]); return; }
    setRows([]);
    setLoading(true); setError(null);
    try {
      const result = await api.get<ResultRow[]>('/api/v1/results', { school_id: selectedSchool.id, student_id: studentId, term_id: termId });
      setRows(result);
    } catch (e) {
      setRows([]);
      setError(e instanceof Error ? e.message : 'Could not load published results.');
    }
    finally { setLoading(false); }
  }, [selectedSchool, studentId, termId]);
  useEffect(() => { void loadResults(); }, [loadResults]);

  const student = students.find(s => s.id === studentId);
  const term = terms.find(t => t.id === termId);
  const average = useMemo(() => {
    const values = rows.map(r => r.weighted_percentage).filter((x): x is number => x !== null);
    return values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length * 100) / 100 : null;
  }, [rows]);

  if (!selectedSchool) return <div><PageHeader title="Report Cards" subtitle="Select a school first."/><Card className="p-6">Choose a school from the selector above.</Card></div>;
  return <div className="space-y-5">
    <div className="print:hidden"><PageHeader title="Report Cards" subtitle={'Generate a printable term report card for ' + selectedSchool.name + '.'} actions={<Button variant="secondary" onClick={() => void loadResults()}>Refresh</Button>}/></div>
    {error && <div className="print:hidden"><ErrorBanner message={error} onRetry={() => { void loadSetup(); void loadResults(); }}/></div>}
    <Card className="p-4 print:hidden">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">Student<select value={studentId} onChange={e=>setStudentId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose student…</option>{students.map(s=><option key={s.id} value={s.id}>{s.first_name} {s.last_name} · {s.student_number}</option>)}</select></label>
        <label className="text-sm font-medium text-slate-700">Term<select value={termId} onChange={e=>setTermId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose term…</option>{terms.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
      </div>
      <div className="mt-4"><Button onClick={() => window.print()} disabled={!student || !term || rows.length===0}>Print / Save PDF</Button></div>
    </Card>
    {loading ? <Card className="p-6"><Spinner label="Preparing report card…"/></Card> : !student || !term ? <Card className="p-6 text-sm text-slate-500">Choose a student and term to generate a report card.</Card> : (
      <div id="report-card" className="mx-auto max-w-4xl border border-slate-200 bg-white p-6 shadow-sm print:max-w-none print:border-0 print:p-0 print:shadow-none">
        <header className="border-b-2 border-slate-800 pb-4 text-center">
          <h1 className="text-2xl font-bold uppercase tracking-wide text-slate-900">{selectedSchool.name}</h1>
          <p className="mt-1 text-sm text-slate-600">{selectedSchool.address || selectedSchool.city || ''}{selectedSchool.country ? ' · ' + selectedSchool.country : ''}</p>
          <h2 className="mt-4 text-lg font-semibold uppercase tracking-widest text-slate-800">Student Report Card</h2>
          <p className="mt-1 text-sm text-slate-600">{term.name}</p>
        </header>
        <section className="grid grid-cols-2 gap-3 border-b border-slate-200 py-4 text-sm sm:grid-cols-3">
          <div><p className="text-xs uppercase tracking-wide text-slate-500">Student name</p><p className="mt-1 font-semibold text-slate-900">{student.first_name} {student.middle_name ? student.middle_name + ' ' : ''}{student.last_name}</p></div>
          <div><p className="text-xs uppercase tracking-wide text-slate-500">Student number</p><p className="mt-1 font-semibold text-slate-900">{student.student_number}</p></div>
          <div><p className="text-xs uppercase tracking-wide text-slate-500">Report date</p><p className="mt-1 font-semibold text-slate-900">{new Date().toLocaleDateString()}</p></div>
        </section>
        {rows.length===0 ? <p className="py-10 text-center text-sm text-slate-500">No published assessment results are available for this student and term.</p> : <>
          <div className="mt-5 overflow-x-auto"><table className="min-w-full border-collapse text-sm"><thead><tr className="bg-slate-100"><th className="border border-slate-300 px-3 py-2 text-left">Subject</th><th className="border border-slate-300 px-3 py-2 text-right">Weighted average</th><th className="border border-slate-300 px-3 py-2 text-center">Grade</th><th className="border border-slate-300 px-3 py-2 text-right">Assessments recorded</th></tr></thead><tbody>{rows.map(row=><tr key={row.subject_id}><td className="border border-slate-300 px-3 py-2 font-medium">{row.subject_name}</td><td className="border border-slate-300 px-3 py-2 text-right">{row.weighted_percentage == null ? '—' : row.weighted_percentage + '%'}</td><td className="border border-slate-300 px-3 py-2 text-center font-semibold">{row.grade_label ?? '—'}</td><td className="border border-slate-300 px-3 py-2 text-right">{row.marks_recorded}/{row.assessments_count}</td></tr>)}</tbody></table></div>
          <div className="mt-5 flex items-center justify-end gap-4 rounded-md bg-slate-50 p-4"><span className="text-sm font-semibold text-slate-700">Overall subject average</span><span className="text-xl font-bold text-slate-900">{average == null ? '—' : average + '%'}</span></div>
          <h3 className="mt-6 font-semibold text-slate-900">Assessment details</h3>
          <div className="mt-2 overflow-x-auto"><table className="min-w-full border-collapse text-sm"><thead><tr className="bg-slate-100"><th className="border border-slate-300 px-3 py-2 text-left">Subject</th><th className="border border-slate-300 px-3 py-2 text-left">Assessment</th><th className="border border-slate-300 px-3 py-2 text-right">Score</th><th className="border border-slate-300 px-3 py-2 text-right">Percent</th><th className="border border-slate-300 px-3 py-2 text-left">Remarks</th></tr></thead><tbody>{rows.flatMap(row=>row.assessments.map(a=><tr key={a.assessment_id}><td className="border border-slate-300 px-3 py-2">{row.subject_name}</td><td className="border border-slate-300 px-3 py-2">{a.title}</td><td className="border border-slate-300 px-3 py-2 text-right">{a.score} / {a.max_score}</td><td className="border border-slate-300 px-3 py-2 text-right">{a.percentage}%</td><td className="border border-slate-300 px-3 py-2">{a.remarks || '—'}</td></tr>))}</tbody></table></div>
        </>}
        <footer className="mt-10 grid grid-cols-2 gap-8 text-sm"><div className="border-t border-slate-400 pt-2">Class teacher signature</div><div className="border-t border-slate-400 pt-2">Head teacher signature</div></footer>
        <p className="mt-8 text-center text-xs text-slate-500">Generated by MeritMatrix Pro · Only published results are included.</p>
      </div>
    )}
  </div>;
}
