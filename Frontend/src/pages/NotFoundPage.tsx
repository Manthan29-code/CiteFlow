import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/common/Button';
import { Home } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-cream flex flex-col items-center justify-center p-6 text-center">
      <span className="font-mono text-xs uppercase tracking-[0.3em] text-indigo-brand font-semibold mb-2">
        Error 404
      </span>
      <h1 className="font-serif text-5xl font-bold text-charcoal-900 mb-3">
        Page Not Found
      </h1>
      <p className="text-sm text-charcoal/60 font-sans max-w-md mb-8">
        The page you are looking for doesn&rsquo;t exist or has been moved to another section.
      </p>
      <Button
        variant="primary"
        onClick={() => navigate('/')}
        className="gap-2"
      >
        <Home className="w-4 h-4" />
        <span>Return to Library</span>
      </Button>
    </div>
  );
};
