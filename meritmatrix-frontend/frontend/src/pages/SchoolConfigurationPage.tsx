import { useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { CountryCode, InstitutionType, SchoolResponse } from '../types';
import { INSTITUTION_TYPES } from '../types';
import { Button, Card, ErrorBanner, Field, Input, PageHeader, Select, Spinner } from '../components/ui';

type SchoolProfile = { registration_number: string; address: string; city: string; country: string; phone: string; email: string; website: string; logo_url: string; timezone: string; currency: string };
const emptyProfile: SchoolProfile = { registration_number: '', address: '', city: '', country: '', phone: '', email: '', website: '', logo_url: '', timezone: '', currency: '' };
type Level = { code: string; name: string; stage: string; sequence: number; requires_review?: boolean };
type CurriculumCycle = { code: string; name: string; levels: string[]; description: string };
type CountryTemplate = { country_code: CountryCode; country_name: string; template_version: number; status: string; timezone: string; currency: string; institution_types: InstitutionType[]; levels: Level[]; curriculum_cycles?: CurriculumCycle[]; curriculum_guidance?: { authority: string; syllabi_url: string; subject_setup: string }; calendar_event_types: string[]; notes: string[] };
const countryOptions = [{ value: 'ZW', label: 'Zimbabwe' }, { value: 'BW', label: 'Botswana' }];

export default function SchoolConfigurationPage() {
  const { selectedSchool, refresh } = useSchool();
  const [countryCode, setCountryCode] = useState<CountryCode | ''>('');
  const [institutionType, setInstitutionType] = useState<InstitutionType | ''>('');
  const [profile, setProfile] = useState<SchoolProfile>(emptyProfile);
  const [template, setTemplate] = useState<CountryTemplate | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    setCountryCode(selectedSchool?.country_code ?? '');
    setInstitutionType(selectedSchool?.institution_type ?? '');
    setProfile({
      registration_number: selectedSchool?.registration_number ?? '',
      address: selectedSchool?.address ?? '',
      city: selectedSchool?.city ?? '',
      country: selectedSchool?.country ?? '',
      phone: selectedSchool?.phone ?? '',
      email: selectedSchool?.email ?? '',
      website: selectedSchool?.website ?? '',
      logo_url: selectedSchool?.logo_url ?? '',
      timezone: selectedSchool?.timezone ?? '',
      currency: selectedSchool?.currency ?? '',
    });
  }, [selectedSchool?.id, selectedSchool?.country_code, selectedSchool?.institution_type, selectedSchool?.registration_number, selectedSchool?.address, selectedSchool?.city, selectedSchool?.country, selectedSchool?.phone, selectedSchool?.email, selectedSchool?.website, selectedSchool?.logo_url, selectedSchool?.timezone, selectedSchool?.currency]);
  useEffect(() => {
    if (!countryCode) { setTemplate(null); return; }
    let cancelled = false; setLoading(true);
    api.get<CountryTemplate>(`/api/v1/country-configurations/${countryCode}`)
      .then((data) => { if (!cancelled) setTemplate(data); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Could not load country template'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [countryCode]);

  const levels = useMemo(() => {
    if (!template) return [];
    if (!institutionType || institutionType === 'combined') return template.levels;
    const stageByType: Record<InstitutionType, string[]> = { early_childhood: ['early_childhood'], primary: ['early_childhood', 'primary'], secondary: ['secondary'], high_school: ['secondary', 'advanced_secondary'], combined: ['early_childhood', 'primary', 'secondary', 'advanced_secondary'], tertiary: [] };
    if (institutionType === 'tertiary') return [];
    return template.levels.filter((level) => stageByType[institutionType].includes(level.stage));
  }, [template, institutionType]);

  async function save() {
    if (!selectedSchool || !countryCode || !institutionType) { setError('Choose a school, country, and institution type before saving.'); return; }
    setSaving(true); setError(null); setSuccess('');
    try {
      const updated = await api.patch<SchoolResponse>(`/api/v1/schools/${selectedSchool.id}`, {
        country_code: countryCode,
        institution_type: institutionType,
        registration_number: profile.registration_number.trim() || null,
        address: profile.address.trim() || null,
        city: profile.city.trim() || null,
        country: profile.country.trim() || template?.country_name || null,
        phone: profile.phone.trim() || null,
        email: profile.email.trim() || null,
        website: profile.website.trim() || null,
        logo_url: profile.logo_url.trim() || null,
        timezone: profile.timezone.trim() || template?.timezone || null,
        currency: profile.currency.trim() || template?.currency || null,
        education_template_version: template?.template_version,
      });
      await refresh();
      setCountryCode(updated.country_code ?? countryCode);
      setInstitutionType(updated.institution_type ?? institutionType);
      setProfile({
        registration_number: updated.registration_number ?? '',
        address: updated.address ?? '', city: updated.city ?? '', country: updated.country ?? '',
        phone: updated.phone ?? '', email: updated.email ?? '', website: updated.website ?? '',
        logo_url: updated.logo_url ?? '', timezone: updated.timezone ?? '', currency: updated.currency ?? '',
      });
      setSuccess(`Saved ${updated.country ?? template?.country_name} configuration for ${updated.name}. Existing classes and records were not changed.`);
    } catch (e) { setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not save configuration'); }
    finally { setSaving(false); }
  }

  if (!selectedSchool) return <div><PageHeader title="School Configuration" /><Card className="p-6">Select a school from the header first.</Card></div>;
  return <div className="space-y-5">
    <PageHeader title="School Configuration" subtitle={`Country, institution type, and education template for ${selectedSchool.name}`} />
    {error && <ErrorBanner message={error} onRetry={() => setError(null)} />}
    {success && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{success}</div>}
    <Card className="space-y-4 p-5">
      <h2 className="text-base font-semibold text-slate-900">School identity and contact details</h2>
      <p className="text-sm text-slate-600">These details belong only to {selectedSchool.name}. The logo is used on printed report cards.</p>
      {profile.logo_url && <div className="flex items-center gap-3 rounded-md border border-slate-200 p-3"><img src={profile.logo_url} alt={selectedSchool.name + ' logo preview'} className="h-16 w-16 object-contain" onError={(event) => { event.currentTarget.style.display = 'none'; }} /><span className="text-sm text-slate-600">Logo preview</span></div>}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Registration number"><Input value={profile.registration_number} onChange={(e) => setProfile(v => ({ ...v, registration_number: e.target.value }))} /></Field>
        <Field label="Phone"><Input value={profile.phone} onChange={(e) => setProfile(v => ({ ...v, phone: e.target.value }))} /></Field>
        <Field label="School email"><Input type="email" value={profile.email} onChange={(e) => setProfile(v => ({ ...v, email: e.target.value }))} /></Field>
        <Field label="Website"><Input type="url" value={profile.website} onChange={(e) => setProfile(v => ({ ...v, website: e.target.value }))} placeholder="https://..." /></Field>
        <Field label="Address"><Input value={profile.address} onChange={(e) => setProfile(v => ({ ...v, address: e.target.value }))} /></Field>
        <Field label="City / town"><Input value={profile.city} onChange={(e) => setProfile(v => ({ ...v, city: e.target.value }))} /></Field>
        <Field label="Country"><Input value={profile.country} onChange={(e) => setProfile(v => ({ ...v, country: e.target.value }))} /></Field>
        <Field label="School logo URL"><Input type="url" value={profile.logo_url} onChange={(e) => setProfile(v => ({ ...v, logo_url: e.target.value }))} placeholder="https://example.com/logo.png" /></Field>
        <Field label="Timezone"><Input value={profile.timezone} onChange={(e) => setProfile(v => ({ ...v, timezone: e.target.value }))} placeholder="Africa/Gaborone" /></Field>
        <Field label="Currency"><Input value={profile.currency} onChange={(e) => setProfile(v => ({ ...v, currency: e.target.value }))} placeholder="BWP" /></Field>
      </div>
    </Card>
    <Card className="space-y-4 p-5">
      <h2 className="text-base font-semibold text-slate-900">Institution profile</h2>
      <p className="text-sm text-slate-600">Each school has its own country and academic settings. Changing these settings does not overwrite existing classes, enrolments, or records.</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-700">Operating country<Select className="mt-1 w-full" value={countryCode} onChange={(e) => { setCountryCode(e.target.value as CountryCode | ''); setSuccess(''); }}><option value="">Select country…</option>{countryOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</Select></label>
        <label className="block text-sm font-medium text-slate-700">Institution type<Select className="mt-1 w-full" value={institutionType} onChange={(e) => { setInstitutionType(e.target.value as InstitutionType | ''); setSuccess(''); }}><option value="">Select institution type…</option>{INSTITUTION_TYPES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</Select></label>
      </div>
      {template && <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold text-slate-900">{template.country_name} education template</p><span className="rounded-full bg-white px-2 py-1 text-xs text-slate-600">Version {template.template_version} · {template.status.replaceAll('_', ' ')}</span></div><p className="mt-2 text-slate-600">Default timezone: {template.timezone} · Currency: {template.currency}</p>{loading ? <Spinner /> : <><h3 className="mt-4 font-medium text-slate-800">Suggested education levels</h3>{levels.length ? <ul className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">{levels.map((level) => <li key={level.code} className="rounded border border-slate-200 bg-white px-3 py-2"><span className="font-medium">{level.name}</span><span className="ml-2 text-xs text-slate-500">{level.stage.replaceAll('_', ' ')}</span>{level.requires_review && <span className="mt-1 block text-xs text-amber-700">Needs authority review</span>}</li>)}</ul> : <p className="mt-2 text-slate-600">Tertiary course and qualification levels must be configured by the institution.</p>}</>}{template.curriculum_cycles && template.curriculum_cycles.length > 0 && <><h3 className="mt-4 font-medium text-slate-800">Secondary curriculum cycles</h3><div className="mt-2 grid gap-3 sm:grid-cols-2">{template.curriculum_cycles.map(cycle => <div key={cycle.code} className="rounded-md border border-slate-200 bg-white p-3"><p className="font-semibold text-slate-900">{cycle.name}</p><p className="mt-1 text-xs text-slate-500">{cycle.levels.map(code => levels.find(level => level.code === code)?.name ?? code).join(' · ')}</p><p className="mt-2 text-sm text-slate-600">{cycle.description}</p></div>)}</div></>}{template.curriculum_guidance && <div className="mt-3 rounded-md border border-slate-200 bg-white p-3"><p className="font-medium text-slate-800">Syllabus and subject setup</p><p className="mt-1 text-sm text-slate-600">{template.curriculum_guidance.subject_setup}</p><a className="mt-2 inline-block text-sm font-medium text-blue-700 underline" href={template.curriculum_guidance.syllabi_url} target="_blank" rel="noreferrer">Open {template.curriculum_guidance.authority} syllabi</a></div>}{template.notes.length > 0 && <><h3 className="mt-4 font-medium text-slate-800">Setup notes</h3><ul className="mt-1 list-disc space-y-1 pl-5 text-slate-600">{template.notes.map((note) => <li key={note}>{note}</li>)}</ul></>}</div>}
      <div className="flex justify-end"><Button onClick={save} disabled={saving || !countryCode || !institutionType}>{saving ? 'Saving…' : 'Save school configuration'}</Button></div>
    </Card>
    <Card className="p-5"><h2 className="font-semibold text-slate-900">Calendar rule</h2><p className="mt-2 text-sm text-slate-600">Country templates are a starting point. Official public holidays, school terms, exam dates, and school-specific closures must be managed separately and verified for the relevant year. Botswana's education-level template remains marked for authority review.</p></Card>
  </div>;
}
