import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../../lib/auth';
import { errorMessage } from '../../lib/api';
import { AuthLayout, AuthField } from './AuthLayout';

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(name, email, password);
      // New account → no workspace yet → landing logic routes to create workspace.
      navigate('/', { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create your workspace"
      subtitle="Your workspace is where your AWS environment and cost data will appear."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="text-emerald-400 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={submit}>
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm px-3 py-2 mb-4">
            {error}
          </div>
        )}
        <AuthField label="Workspace name" value={name} onChange={setName} placeholder="Acme Technologies" autoComplete="organization" />
        <AuthField label="Email" type="email" value={email} onChange={setEmail} placeholder="you@company.com" autoComplete="email" />
        <AuthField label="Password" type="password" value={password} onChange={setPassword} placeholder="At least 6 characters" autoComplete="new-password" />

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-medium mt-2"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          Continue
        </button>
      </form>
    </AuthLayout>
  );
}
