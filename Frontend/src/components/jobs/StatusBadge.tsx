import React from 'react';
import {
  Clock,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  FileCode,
} from 'lucide-react';
import { JobResponse, JobStatus } from '@/types/api';
import { useAppDispatch } from '@/store/hooks';
import {
  openTitleConfirmModal,
  openReviewModal,
} from '@/store/slices/jobsSlice';
import { cn } from '@/lib/utils';

export interface StatusBadgeProps {
  job: JobResponse;
  className?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ job, className, size = 'sm' }) => {
  const dispatch = useAppDispatch();

  const isInteractive =
    job.status === 'needs_title_confirmation' || job.status === 'needs_review';

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();

    if (job.status === 'needs_title_confirmation') {
      dispatch(openTitleConfirmModal(job.id));
    } else if (job.status === 'needs_review') {
      dispatch(openReviewModal(job.id));
    }
  };

  const getBadgeConfig = (status: JobStatus) => {
    switch (status) {
      case 'queued':
        return {
          label: 'Queued',
          icon: <Clock className="w-3 h-3 text-charcoal/60" />,
          styles: 'bg-cream-200 text-charcoal-700 border-border-light',
        };
      case 'running':
        return {
          label: 'Processing',
          icon: <Loader2 className="w-3 h-3 text-indigo-brand animate-spin" />,
          styles: 'bg-indigo-50 text-indigo-brand border-indigo-200',
        };
      case 'needs_title_confirmation':
        return {
          label: 'Confirm Title',
          icon: <AlertTriangle className="w-3 h-3 text-amber-600 animate-pulse" />,
          styles: 'bg-amber-50 text-amber-900 border-amber-300 hover:bg-amber-100 ring-1 ring-amber-400/30 cursor-pointer',
        };
      case 'needs_review':
        return {
          label: 'Review Needed',
          icon: <AlertTriangle className="w-3 h-3 text-amber-600 animate-pulse" />,
          styles: 'bg-amber-50 text-amber-900 border-amber-300 hover:bg-amber-100 ring-1 ring-amber-400/30 cursor-pointer',
        };
      case 'succeeded':
        return {
          label: 'Citation Ready',
          icon: <CheckCircle2 className="w-3 h-3 text-emerald-600" />,
          styles: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        };
      case 'unresolved':
        return {
          label: 'Unconfirmed',
          icon: <HelpCircle className="w-3 h-3 text-orange-600" />,
          styles: 'bg-orange-50 text-orange-800 border-orange-200',
        };
      case 'failed':
        return {
          label: 'Failed',
          icon: <XCircle className="w-3 h-3 text-red-600" />,
          styles: 'bg-red-50 text-red-700 border-red-200',
        };
      case 'canceled':
        return {
          label: 'Canceled',
          icon: <XCircle className="w-3 h-3 text-charcoal/40" />,
          styles: 'bg-charcoal/5 text-charcoal/60 border-border-light',
        };
      case 'expired':
        return {
          label: 'Expired',
          icon: <Clock className="w-3 h-3 text-charcoal/40" />,
          styles: 'bg-charcoal/5 text-charcoal/60 border-border-light',
        };
      default:
        return {
          label: status,
          icon: <FileCode className="w-3 h-3 text-charcoal/60" />,
          styles: 'bg-cream-200 text-charcoal-700 border-border-light',
        };
    }
  };

  const config = getBadgeConfig(job.status);
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px] gap-1.5' : 'px-3 py-1 text-xs gap-2';

  if (!isInteractive) {
    return (
      <span
        title={config.label}
        className={cn(
          'inline-flex items-center rounded-lg border font-mono tracking-wide font-medium shadow-2xs select-none cursor-default',
          sizeClasses,
          config.styles,
          className
        )}
      >
        {config.icon}
        <span>{config.label}</span>
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={`Job status: ${config.label}`}
      title={`Click to resolve: ${config.label}`}
      className={cn(
        'inline-flex items-center rounded-lg border font-mono tracking-wide font-medium transition-all shadow-2xs select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand',
        sizeClasses,
        config.styles,
        className
      )}
    >
      {config.icon}
      <span>{config.label}</span>
    </button>
  );
};
