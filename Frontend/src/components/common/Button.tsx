import React, { forwardRef } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: 'primary' | 'secondary' | 'destructive' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
  children?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading = false, disabled, children, ...props }, ref) => {
    const baseStyles =
      'relative inline-flex items-center justify-center font-sans font-medium transition-colors select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none rounded-xl';

    const variants = {
      primary:
        'bg-indigo-brand text-white hover:bg-indigo-hover active:bg-indigo-900 shadow-sm hover:shadow-indigo-soft',
      secondary:
        'bg-cream-200 text-charcoal-900 hover:bg-cream-300 border border-border-light',
      destructive:
        'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 shadow-sm',
      ghost:
        'bg-transparent text-charcoal-800 hover:bg-black/5 active:bg-black/10',
      outline:
        'bg-transparent border border-border-light text-charcoal-800 hover:bg-cream-200 hover:border-charcoal/20',
    };

    const sizes = {
      sm: 'text-xs px-3 py-1.5 gap-1.5',
      md: 'text-sm px-4 py-2 gap-2',
      lg: 'text-base px-6 py-2.5 gap-2.5',
      icon: 'p-2 w-9 h-9',
    };

    return (
      <motion.button
        ref={ref}
        whileTap={{ scale: 0.98 }}
        whileHover={{ scale: 1.01 }}
        transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';
