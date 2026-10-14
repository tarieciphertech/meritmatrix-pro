import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest, ApiError } from '../lib/api';
import { Button, Field, Input } from '../components/ui';

interface ActivationResult { message: string }

export default function GuardianActivationPage() {
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      const result = await apiRequest<ActivationResult>(
        '/api/v1/guardian-accounts/activate',
        { method: 'POST', body: { activation_code: code.trim(), password }, auth: false },
      );
      setSuccess(result.message);
      setCode('');
      setPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to activate the account. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-8">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-600 text-lg font-bold text-white">M</div>
          <h1 className="text-xl font-semibold text-slate-900">Activate Guardian Account</h1>
          <p className="mt-1 text-sm text-slate-500">Create your private password to access the Guardian Portal.</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 rounded-lg bg-white p-6 shadow-sm ring-1 ring-slate-200">
          {error && <div role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
          {success && <div role="status" className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">{success}<div className="mt-2"><Link className="font-medium underline" to="/login">Go to sign in</Link></div></div>}
          <Field label="One-time activation code" required>
            <Input required autoComplete="one-time-code" value={code} onChange={event => setCode(event.target.value)} placeholder="Enter the code given by your school" />
          </Field>
          <Field label="Create password" required>
            <Input required type="password" autoComplete="new-password" minLength={8} value={password} onChange={event => setPassword(event.target.value)} placeholder="At least 8 characters; mix letters and numbers" />
          </Field>
          <Field label="Confirm password" required>
            <Input required type="password" autoComplete="new-password" minLength={8} value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} />
          </Field>
          <Button type="submit" disabled={submitting} className="w-full">{submitting ? 'Activating…' : 'Activate account'}</Button>
          <p className="text-center text-sm text-slate-500"><Link className="underline" to="/login">Back to sign in</Link></p>
        </form>
      </div>
    </div>
  );
}
