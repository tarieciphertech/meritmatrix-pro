import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { AcademicYearResponse, StudentResponse, TermResponse } from '../types';
import { Button, Card, ErrorBanner, PageHeader, Spinner } from '../components/ui';

type Charge = { id: string; student_id: string; student_number: string; student_name: string; academic_year_id: string; academic_year_name: string; term_name: string | null; description: string; amount: number; amount_paid: number; balance: number; due_date: string | null; is_void: boolean };
type Payment = { id: string; student_id: string; student_number: string; student_name: string; charge_id: string; charge_description: string; payment_date: string; amount: number; method: string; reference: string | null };
const today = () => { const d = new Date(); return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-'); };

export default function FeesPage() {
  const { selectedSchool } = useSchool();
  const [students, setStudents] = useState<StudentResponse[]>([]);
  const [years, setYears] = useState<AcademicYearResponse[]>([]);
  const [terms, setTerms] = useState<TermResponse[]>([]);
  const [charges, setCharges] = useState<Charge[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [studentId, setStudentId] = useState('');
  const [yearId, setYearId] = useState('');
  const [termId, setTermId] = useState('');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [chargeId, setChargeId] = useState('');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState(today());
  const [method, setMethod] = useState('cash');
  const [reference, setReference] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const activeSchoolIdRef = useRef<string | null>(selectedSchool?.id ?? null);
  const loadRequestIdRef = useRef(0);

  const load = useCallback(async () => {
    if (!selectedSchool) {
      setStudents([]); setYears([]); setTerms([]); setCharges([]); setPayments([]);
      setLoading(false);
      return;
    }
    const requestSchoolId = selectedSchool.id;
    const requestId = ++loadRequestIdRef.current;
    setStudents([]); setYears([]); setTerms([]); setCharges([]); setPayments([]);
    setLoading(true); setError(null);
    try {
      const [studentRows, yearRows, chargeRows, paymentRows] = await Promise.all([
        api.get<StudentResponse[]>('/api/v1/students', { school_id: requestSchoolId }),
        api.get<AcademicYearResponse[]>('/api/v1/academic-years', { school_id: requestSchoolId }),
        api.get<Charge[]>('/api/v1/fees/charges', { school_id: requestSchoolId }),
        api.get<Payment[]>('/api/v1/fees/payments', { school_id: requestSchoolId }),
      ]);
      if (activeSchoolIdRef.current !== requestSchoolId || loadRequestIdRef.current !== requestId) return;
      setStudents(studentRows.filter(s => s.is_active));
      setYears(yearRows.filter(y => y.is_active));
      setCharges(chargeRows);
      setPayments(paymentRows);
      setStudentId(current => studentRows.some(s => s.id === current && s.is_active) ? current : studentRows.find(s => s.is_active)?.id ?? '');
      setYearId(current => yearRows.some(y => y.id === current && y.is_active) ? current : yearRows.find(y => y.is_current)?.id ?? yearRows.find(y => y.is_active)?.id ?? '');
      const groups = await Promise.all(yearRows.map(y => api.get<TermResponse[]>('/api/v1/terms', { academic_year_id: y.id }).catch(() => [] as TermResponse[])));
      if (activeSchoolIdRef.current !== requestSchoolId || loadRequestIdRef.current !== requestId) return;
      const termRows = groups.flat().filter(t => t.is_active);
      setTerms(termRows);
      setTermId(current => termRows.some(t => t.id === current) ? current : termRows.find(t => t.is_current)?.id ?? '');
      setChargeId(current => chargeRows.some(c => c.id === current && c.balance > 0) ? current : chargeRows.find(c => c.balance > 0)?.id ?? '');
    } catch (e) {
      if (activeSchoolIdRef.current === requestSchoolId && loadRequestIdRef.current === requestId) {
        setStudents([]); setYears([]); setTerms([]); setCharges([]); setPayments([]);
        setError(e instanceof Error ? e.message : 'Could not load fee records.');
      }
    } finally {
      if (activeSchoolIdRef.current === requestSchoolId && loadRequestIdRef.current === requestId) setLoading(false);
    }
  }, [selectedSchool]);

  useEffect(() => {
    activeSchoolIdRef.current = selectedSchool?.id ?? null;
    loadRequestIdRef.current += 1;
    setStudents([]); setYears([]); setTerms([]); setCharges([]); setPayments([]);
    setStudentId(''); setYearId(''); setTermId(''); setChargeId('');
    setDescription(''); setAmount(''); setDueDate(''); setPaymentAmount(''); setPaymentDate(today()); setMethod('cash'); setReference('');
    setError(null); setNotice('');
  }, [selectedSchool?.id]);

  useEffect(() => { void load(); }, [load]);

  async function createCharge() {
    if (!selectedSchool || !studentId || !yearId || !description.trim() || !(Number(amount) > 0)) { setError('Choose a student and academic year, and enter a description and positive amount.'); return; }
    setSaving(true); setError(null); setNotice('');
    try {
      await api.post('/api/v1/fees/charges', {
        student_id: studentId, academic_year_id: yearId, term_id: termId || null,
        description: description.trim(), amount: Number(amount), due_date: dueDate || null,
      }, { school_id: selectedSchool.id });
      setDescription(''); setAmount(''); setDueDate('');
      setNotice('Fee charge recorded.');
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not create fee charge.'); }
    finally { setSaving(false); }
  }

  async function recordPayment() {
    if (!selectedSchool || !chargeId || !(Number(paymentAmount) > 0) || !paymentDate) { setError('Select an outstanding charge and enter a positive payment amount and date.'); return; }
    setSaving(true); setError(null); setNotice('');
    try {
      await api.post('/api/v1/fees/payments', {
        charge_id: chargeId, amount: Number(paymentAmount), payment_date: paymentDate,
        method, reference: reference.trim() || null,
      }, { school_id: selectedSchool.id });
      setPaymentAmount(''); setReference('');
      setNotice('Payment recorded and receipt reference saved.');
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not record payment.'); }
    finally { setSaving(false); }
  }

  const currency = selectedSchool?.currency ? selectedSchool.currency + ' ' : '';
  const outstanding = charges.filter(c => !c.is_void && c.balance > 0);
  const totalCharges = charges.filter(c => !c.is_void).reduce((sum, c) => sum + c.amount, 0);
  const totalPaid = charges.filter(c => !c.is_void).reduce((sum, c) => sum + c.amount_paid, 0);
  if (!selectedSchool) return <div><PageHeader title="Fees & Payments" subtitle="Select a school to manage its fee ledger."/><Card className="p-6">Choose a school from the selector above.</Card></div>;

  return <div className="space-y-5">
    <PageHeader title="Fees & Payments" subtitle={'Record student charges, payments and balances for ' + selectedSchool.name + '.'} actions={<Button variant="secondary" onClick={() => void load()}>Refresh</Button>} />
    {error && <ErrorBanner message={error} onRetry={() => void load()} />}
    {notice && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    {loading ? <Card className="p-6"><Spinner label="Loading fee ledger…"/></Card> : <>
      <div className="grid gap-3 sm:grid-cols-3">
        {[['Total charges', totalCharges], ['Total paid', totalPaid], ['Outstanding', totalCharges-totalPaid]].map(([label, value]) => <Card key={label} className="p-4"><p className="text-sm text-slate-500">{label}</p><p className="mt-1 text-2xl font-semibold text-slate-900">{currency}{Number(value).toLocaleString(undefined,{maximumFractionDigits:2})}</p></Card>)}
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="p-4">
          <h2 className="font-semibold text-slate-900">Add a fee charge</h2>
          <div className="mt-3 space-y-3">
            <label className="block text-sm font-medium text-slate-700">Student<select value={studentId} onChange={e=>setStudentId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose student…</option>{students.map(s=><option key={s.id} value={s.id}>{s.first_name} {s.last_name} · {s.student_number}</option>)}</select></label>
            <label className="block text-sm font-medium text-slate-700">Academic year<select value={yearId} onChange={e=>setYearId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose year…</option>{years.map(y=><option key={y.id} value={y.id}>{y.name}</option>)}</select></label>
            <label className="block text-sm font-medium text-slate-700">Term (optional)<select value={termId} onChange={e=>setTermId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Whole year / not term-specific</option>{terms.filter(t=>t.academic_year_id===yearId).map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
            <label className="block text-sm font-medium text-slate-700">Description<input value={description} onChange={e=>setDescription(e.target.value)} placeholder="Tuition, transport, exam fee…" className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label>
            <div className="grid gap-3 sm:grid-cols-2"><label className="block text-sm font-medium text-slate-700">Amount<input type="number" min="0.01" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label><label className="block text-sm font-medium text-slate-700">Due date<input type="date" value={dueDate} onChange={e=>setDueDate(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label></div>
            <Button onClick={()=>void createCharge()} disabled={saving||!studentId||!yearId}>{saving?'Saving…':'Add charge'}</Button>
          </div>
        </Card>
        <Card className="p-4">
          <h2 className="font-semibold text-slate-900">Record a payment</h2>
          <div className="mt-3 space-y-3">
            <label className="block text-sm font-medium text-slate-700">Outstanding charge<select value={chargeId} onChange={e=>setChargeId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="">Choose charge…</option>{outstanding.map(c=><option key={c.id} value={c.id}>{c.student_name} · {c.description} · balance {currency}{c.balance}</option>)}</select></label>
            <div className="grid gap-3 sm:grid-cols-2"><label className="block text-sm font-medium text-slate-700">Amount<input type="number" min="0.01" step="0.01" value={paymentAmount} onChange={e=>setPaymentAmount(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label><label className="block text-sm font-medium text-slate-700">Payment date<input type="date" value={paymentDate} onChange={e=>setPaymentDate(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label></div>
            <label className="block text-sm font-medium text-slate-700">Method<select value={method} onChange={e=>setMethod(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2"><option value="cash">Cash</option><option value="bank_transfer">Bank transfer</option><option value="mobile_money">Mobile money</option><option value="card">Card</option><option value="other">Other</option></select></label>
            <label className="block text-sm font-medium text-slate-700">Receipt / reference (optional)<input value={reference} onChange={e=>setReference(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 p-2"/></label>
            <Button onClick={()=>void recordPayment()} disabled={saving||!chargeId}>{saving?'Saving…':'Record payment'}</Button>
          </div>
        </Card>
      </div>
      <Card className="overflow-hidden">
        <div className="border-b border-slate-200 p-4"><h2 className="font-semibold text-slate-900">Fee charges</h2></div>
        {charges.length===0?<p className="p-6 text-sm text-slate-500">No fee charges recorded yet.</p>:<div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-sm"><thead className="bg-slate-50"><tr>{['Student','Charge','Academic year','Due date','Charged','Paid','Balance'].map(x=><th key={x} className="px-3 py-3 text-left font-semibold text-slate-600">{x}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{charges.map(c=><tr key={c.id}><td className="px-3 py-3"><p className="font-medium">{c.student_name}</p><p className="text-xs text-slate-500">{c.student_number}</p></td><td className="px-3 py-3">{c.description}{c.term_name?' · '+c.term_name:''}</td><td className="px-3 py-3">{c.academic_year_name}</td><td className="px-3 py-3">{c.due_date||'—'}</td><td className="px-3 py-3">{currency}{c.amount}</td><td className="px-3 py-3">{currency}{c.amount_paid}</td><td className="px-3 py-3 font-semibold">{currency}{c.balance}</td></tr>)}</tbody></table></div>}
      </Card>
      <Card className="overflow-hidden">
        <div className="border-b border-slate-200 p-4"><h2 className="font-semibold text-slate-900">Recent payments</h2></div>
        {payments.length===0?<p className="p-6 text-sm text-slate-500">No payments recorded yet.</p>:<div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-sm"><thead className="bg-slate-50"><tr>{['Date','Student','Charge','Method','Reference','Amount'].map(x=><th key={x} className="px-3 py-3 text-left font-semibold text-slate-600">{x}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{payments.map(p=><tr key={p.id}><td className="px-3 py-3">{p.payment_date}</td><td className="px-3 py-3">{p.student_name}</td><td className="px-3 py-3">{p.charge_description}</td><td className="px-3 py-3">{p.method.replaceAll('_',' ')}</td><td className="px-3 py-3">{p.reference||'—'}</td><td className="px-3 py-3 font-semibold">{currency}{p.amount}</td></tr>)}</tbody></table></div>}
      </Card>
    </>}
  </div>;
}
