// Login screen: email + password against POST /api/v1/auth/login.

import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { ApiError } from '../lib/api';
import { Button, Field, Input } from '../components/ui';

export default function LoginPage() {
  const { user, initializing, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already authenticated → go to the page they wanted (or dashboard).
  if (!initializing && user) {
    const from = (location.state as { from?: string } | null)?.from ?? '/';
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(identifier, password);
      const from = (location.state as { from?: string } | null)?.from ?? '/';
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Unable to reach the server. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-transparent px-4 py-10">
      <div className="w-full max-w-sm rounded-2xl border border-white/40 bg-white/95 p-7 shadow-2xl shadow-slate-950/30 backdrop-blur-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-sky-500 text-lg font-bold text-white shadow-lg shadow-indigo-900/20">
            M
          </div>
          <h1 className="text-xl font-semibold text-slate-900">MeritMatrix Pro</h1>
          <p className="mt-1 text-sm text-slate-500">Your school, connected.</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="mt-5 space-y-4 rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm"
        >
          {error && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
              {error}
            </div>
          )}

          <Field label="Email or phone number" required>
            <Input
              type="text"
              autoComplete="username"
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="you@school.edu or +263..."
            />
          </Field>

          <Field label="Password" required>
            <Input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </Field>

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </div>
    </div>
  );
}