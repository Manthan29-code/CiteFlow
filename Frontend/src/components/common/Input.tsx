import React, { forwardRef, useId } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  endAdornment?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', label, error, helperText, endAdornment, id: providedId, ...props }, ref) => {
    const generatedId = useId();
    const id = providedId || generatedId;
    const errorId = `${id}-error`;
    const helperId = `${id}-helper`;

    return (
      <div className="w-full text-left">
        {label && (
          <label htmlFor={id} className="block text-xs font-mono tracking-wide uppercase text-charcoal/80 mb-1.5 font-medium">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          <input
            ref={ref}
            id={id}
            type={type}
            aria-invalid={!!error}
            aria-describedby={error ? errorId : helperText ? helperId : undefined}
            className={cn(
              'w-full px-3.5 py-2.5 rounded-xl bg-white border border-border-light text-charcoal-900 placeholder:text-charcoal/40 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-indigo-brand focus:border-transparent disabled:bg-cream-200 disabled:opacity-60 shadow-sm',
              error && 'border-red-500 focus:ring-red-500',
              endAdornment && 'pr-10',
              className
            )}
            {...props}
          />
          {endAdornment && (
            <div className="absolute right-3 flex items-center pointer-events-auto">
              {endAdornment}
            </div>
          )}
        </div>
        {error && (
          <p id={errorId} className="mt-1.5 text-xs text-red-600 font-sans" role="alert">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={helperId} className="mt-1 text-xs text-charcoal/60 font-sans">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
