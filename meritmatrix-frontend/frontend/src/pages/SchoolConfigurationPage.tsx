import { useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { useSchool } from '../lib/school-context';
import type { CountryCode, InstitutionType, SchoolResponse } from '../types';
import { INSTITUTION_TYPES } from '../types';
import { Button, Card, ErrorBanner, PageHeader, Select, Spinner } from '../components/ui';

type Level = { code: string; name: string; stage: string; sequence: number; requires_review?: boolean };
type CountryTemplate = {
  country_code: CountryCode;
  country_name: string;
  template_version: number;
  status: string;
  timezone: string;
  currency: string;
  institution_types: InstitutionType[];
  levels: Level[];
  calendar_event_types: string[];
  notes: string[];
};

const countryOptions = [
  { value: 'ZW', label: 'Zimbabwe' },
  { value: 'BW', label: 'Botswana' },
];

export default function SchoolConfigurationPage() {
  const { selectedSchool } = useSchool();
  const [countryCode, setCountryCode] = useState<CountryCode | ''>('');
  const [institutionType, setInstitutionType] = useState<InstitutionType | ''>('');
  const [template, setTemplate] = useState<CountryTemplate | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    setCountryCode(selectedSchool?.country_code ?? '');
    setInstitutionType(selectedSchool?.institution_type ?? '');
  }, [selectedSchool?.id, selectedSchool?.country_code, selectedSchool?.institution_type]);

  useEffect(() => {
    if (!countryCode) { setTemplate(null); return; }
    let cancelled = false;
    setLoading(true);
    api.get<CountryTemplate>(`/api/v1/country-configurations/${countryCode}`)
      .then((data) => { if (!cancelled) setTemplate(data); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Could not load country template'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [countryCode]);

  const levels = useMemo(() => {
    if (!template) return [];
    if (!institutionType || institutionType === 'combined') return template.levels;
    const stageByType: Record<InstitutionType, string[]> = {
      early_childhood: ['early_childhood'],
      primary: ['early_childhood', 'primary'],
      secondary: ['secondary', 'advanced_secondary'],
      combined: ['early_childhood', 'primary', 'secondary', 'advanced_secondary'],
      tertiary: ['tertiary'],
    };
    // Tertiary programs use institution-defined structures and are not guessed
    // from primary/secondary country templates.
    if (institutionType === 'tertiary') return [];
    return template.levels.filter((level) => stageByType[institutionType].includes(level.stage));
  }, [template, institutionType]);

  async function save() {
    if (!selectedSchool || !countryCode || !institutionType) {
      setError('Choose a school, country, and institution type before saving.');
      return;
    }
    setSaving(true); setError(null); setSuccess('');
    try {
      const updated = await api.patch<SchoolResponse>(`/api/v1/schools/${selectedSchool.id}`, {
        country_code: countryCode,
        institution_type: institutionType,
        country: template?.country_name,
        timezone: template?.timezone,
        currency: template?.currency,
        education_template_version: template?.template_version,
      });
      setCountryCode(updated.country_code ?? countryCode);
      setInstitutionType(updated.institution_type ?? institutionType);
      setSuccess(`Saved ${updated.country ?? template?.country_name} configuration for ${updated.name}. Existing classes and records were not changed.`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Could not save configuration');
    } finally { setSaving(false); }
  }

  if (!selectedSchool) {
    return <div><PageHeader title="School Configuration" /><Card className="p-6">Select a school from the header first.</Card></div>;
  }

  return (
    <div className="space-y-5">
      <PageHeader title="School Configuration" subtitle={`Country, institution type, and education template for ${selectedSchool.name}`} />
      {error && <ErrorBanner message={error} onRetry={() => setError(null)} />}
      {success && <div role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{success}</div>}
      <Card className="space-y-4 p-5">
        <h2 className="text-base font-semibold text-slate-900">Institution profile</h2>
        <p className="text-sm text-slate-600">Every school has its own country and academic settings. Changing these settings does not overwrite existing classes, enrolments, or school records.</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium text-slate-700">Operating country
            <Select className="mt-1 w-full" value={countryCode} onChange={(e) => { setCountryCode(e.target.value as CountryCode | ''); setSuccess(''); }}>
              <option value="">Select country…</option>
              {countryOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </Select>
          </label>
          <label className="block text-sm font-medium text-slate-700">Institution type
            <Select className="mt-1 w-full" value={institutionType} onChange={(e) => { setInstitutionType(e.target.value as InstitutionType | ''); setSuccess(''); }}>
              <option value="">Select institution type…</option>
              {INSTITUTION_TYPES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </Select>
          </label>
        </div>
        {template && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold text-slate-900">{template.country_name} education template</p>
              <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-600">Version {template.template_version} · {template.status.replaceAll('_', ' ')}</span>
            </div>
            <p className="mt-2 text-slate-600">Default timezone: {template.timezone} · Currency: {template.currency}</p>
            {loading ? <Spinner /> : (
              <>
                <h3 className="mt-4 font-medium text-slate-800">Suggested education levels</h3>
                {levels.length ? <ul className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">{levels.map((level) => <li key={level.code} className="rounded border border-slate-200 bg-white px-3 py-2"><span className="font-medium">{level.name}</span><span className="ml-2 text-xs text-slate-500">{level.stage.replaceAll('_', ' ')}</span>{level.requires_review && <span className="mt-1 block text-xs text-amber-700">Needs authority review</span>}</li>)}</ul> : <p className="mt-2 text-slate-600">Tertiary course and qualification levels must be configured by the institution.</p>}
              </>
            )}
            {template.notes.length > 0 && <><h3 className="mt-4 font-medium text-slate-800">Setup notes</h3><ul className="mt-1 list-disc space-y-1 pl-5 text-slate-600">{template.notes.map((note) => <li key={note}>{note}</li>)}</ul></>}
          </div>
        )}
        <div className="flex justify-end"><Button onClick={save} disabled={saving || !countryCode || !institutionType}>{saving ? 'Saving…' : 'Save school configuration'}</Button></div>
      </Card>
      <Card className="p-5">
        <h2 className="font-semibold text-slate-900">Important calendar rule</h2>
        <p className="mt-2 text-sm text-slate-600">Country templates provide a starting point only. Official public holidays, school terms, examination dates, and institution-specific closures must be managed separately and verified for the relevant year. Botswana's education-level template is still marked for authority review.</p>
      </Card>
    </div>
  );
}
