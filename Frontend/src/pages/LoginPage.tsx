import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { BookOpen, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import { getSafeRedirectPath } from '@/lib/safeRedirect';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, isLoading, error, clearError } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);

  const rawNext = searchParams.get('next');
  const safeNext = getSafeRedirectPath(rawNext);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);
    clearError();

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setClientError('Please enter your email.');
      return;
    }

    if (!/\S+@\S+\.\S+/.test(trimmedEmail)) {
      setClientError('Please enter a valid email address.');
      return;
    }

    if (!password) {
      setClientError('Please enter your password.');
      return;
    }

    const success = await login({ email: trimmedEmail, password });
    if (success) {
      navigate(safeNext);
    }
  };

  const displayError = clientError || error;

  return (
    <div className="min-h-screen w-full flex flex-col justify-center items-center px-4 py-12 mesh-gradient-bg bg-cream relative">
      {/* Brand Header */}
      <div className="mb-8 text-center flex flex-col items-center">
        <div className="w-12 h-12 rounded-2xl bg-charcoal-900 text-white flex items-center justify-center shadow-lg mb-3">
          <BookOpen className="w-6 h-6 text-indigo-300" />
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl font-bold tracking-tight text-charcoal-900 m-0">
          Cite<span className="italic font-normal text-indigo-brand">Flow</span>
        </h1>
        <p className="mt-2 text-xs font-mono uppercase tracking-[0.3em] text-charcoal/60">
          Intelligent Document Library
        </p>
      </div>

      {/* Login Card */}
      <div className="w-full max-w-md bg-white rounded-3xl border border-border-light shadow-2xl p-8 sm:p-10 relative z-10">
        <div className="mb-6">
          <h2 className="font-serif text-2xl font-bold text-charcoal-900 m-0">
            Sign In
          </h2>
          <p className="mt-1 text-xs font-sans text-charcoal/60">
            Enter your credentials to access your research papers.
          </p>
        </div>

        {displayError && (
          <div
            className="mb-5 p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs font-sans text-red-700"
            role="alert"
          >
            {displayError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email Address"
            type="email"
            autoComplete="email"
            placeholder="researcher@university.edu"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (clientError) setClientError(null);
            }}
            disabled={isLoading}
            autoFocus
          />

          <Input
            label="Password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (clientError) setClientError(null);
            }}
            disabled={isLoading}
            endAdornment={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-charcoal/40 hover:text-charcoal p-1 transition-colors"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            }
          />

          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full gap-2 text-sm"
              isLoading={isLoading}
            >
              <span>Sign In to Library</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </form>

        <div className="mt-6 pt-6 border-t border-border-light text-center text-xs text-charcoal/60 font-sans">
          Don&rsquo;t have an account yet?{' '}
          <Link
            to={rawNext ? `/register?next=${encodeURIComponent(rawNext)}` : '/register'}
            className="font-medium text-indigo-brand hover:underline font-mono"
          >
            Register
          </Link>
        </div>
      </div>

      {/* Footer minimal tag */}
      <div className="mt-8 text-center text-[11px] font-mono uppercase tracking-[0.2em] text-charcoal/40">
        CiteFlow Core &bull; Secure Cookie Session
      </div>
    </div>
  );
};
