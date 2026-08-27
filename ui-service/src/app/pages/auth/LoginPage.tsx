import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../../lib/auth';
import { errorMessage } from '../../lib/api';
import { AuthLayout, AuthField } from './AuthLayout';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Sign in to your workspace"
      subtitle="Enter your credentials to access your environment."
      footer={
        <>
          Don&apos;t have an account?{' '}
          <Link to="/register" className="text-emerald-400 hover:underline">
            Create workspace
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
        <AuthField label="Email" type="email" value={email} onChange={setEmail} placeholder="you@company.com" autoComplete="email" />
        <AuthField label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" autoComplete="current-password" />

        <div className="flex justify-end mb-5 -mt-1">
          <button
            type="button"
            onClick={() => setError('Password reset is not available in this preview.')}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            Forgot password?
          </button>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-medium"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          Sign in
        </button>
      </form>
    </AuthLayout>
  );
}
