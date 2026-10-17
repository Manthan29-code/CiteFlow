import React from 'react';
import { cn } from '@/lib/utils';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className, label }) => {
  const sizeMap = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-2',
    lg: 'w-12 h-12 border-3',
  };

  return (
    <div className={cn('flex flex-col items-center justify-center gap-3', className)} role="status">
      <div
        className={cn(
          'rounded-full border-border-light border-t-indigo-brand animate-spin',
          sizeMap[size]
        )}
      />
      {label && (
        <span className="text-xs font-mono uppercase tracking-[0.3em] text-charcoal/60">
          {label}
        </span>
      )}
      <span className="sr-only">Loading...</span>
    </div>
  );
};
