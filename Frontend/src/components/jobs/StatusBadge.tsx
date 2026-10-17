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
  openJobDrawer,
  openTitleConfirmModal,
  openReviewModal,
  openTexPreviewModal,
} from '@/store/slices/jobsSlice';
import { cn } from '@/lib/utils';

export interface StatusBadgeProps {
  job: JobResponse;
  className?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ job, className, size = 'sm' }) => {
  const dispatch = useAppDispatch();

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();

    if (job.status === 'needs_title_confirmation') {
      dispatch(openTitleConfirmModal(job.id));
    } else if (job.status === 'needs_review') {
      dispatch(openReviewModal(job.id));
    } else if (job.status === 'succeeded') {
      dispatch(openTexPreviewModal(job.id));
    } else {
      dispatch(openJobDrawer(job.id));
    }
  };

  const getBadgeConfig = (status: JobStatus) => {
    switch (status) {
      case 'queued':
        return {
          label: 'Queued',
          icon: <Clock className="w-3 h-3 text-charcoal/60" />,
          styles: 'bg-cream-200 text-charcoal-700 border-border-light hover:bg-cream-300',
        };
      case 'running':
        return {
          label: 'Processing',
          icon: <Loader2 className="w-3 h-3 text-indigo-brand animate-spin" />,
          styles: 'bg-indigo-50 text-indigo-brand border-indigo-200 hover:bg-indigo-100',
        };
      case 'needs_title_confirmation':
        return {
          label: 'Confirm Title',
          icon: <AlertTriangle className="w-3 h-3 text-amber-600 animate-pulse" />,
          styles: 'bg-amber-50 text-amber-900 border-amber-300 hover:bg-amber-100 ring-1 ring-amber-400/30',
        };
      case 'needs_review':
        return {
          label: 'Review Metadata',
          icon: <AlertTriangle className="w-3 h-3 text-amber-600 animate-pulse" />,
          styles: 'bg-amber-50 text-amber-900 border-amber-300 hover:bg-amber-100 ring-1 ring-amber-400/30',
        };
      case 'succeeded':
        return {
          label: 'Citation Ready',
          icon: <CheckCircle2 className="w-3 h-3 text-emerald-600" />,
          styles: 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100',
        };
      case 'unresolved':
        return {
          label: 'Unconfirmed',
          icon: <HelpCircle className="w-3 h-3 text-orange-600" />,
          styles: 'bg-orange-50 text-orange-800 border-orange-200 hover:bg-orange-100',
        };
      case 'failed':
        return {
          label: 'Failed',
          icon: <XCircle className="w-3 h-3 text-red-600" />,
          styles: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100',
        };
      case 'canceled':
        return {
          label: 'Canceled',
          icon: <XCircle className="w-3 h-3 text-charcoal/40" />,
          styles: 'bg-charcoal/5 text-charcoal/60 border-border-light hover:bg-charcoal/10',
        };
      case 'expired':
        return {
          label: 'Expired',
          icon: <Clock className="w-3 h-3 text-charcoal/40" />,
          styles: 'bg-charcoal/5 text-charcoal/60 border-border-light hover:bg-charcoal/10',
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

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={`Job status: ${config.label}`}
      title={
        job.status === 'succeeded'
          ? 'Citation ready - Click to view .tex output'
          : `Click to view citation pipeline (${config.label})`
      }
      className={cn(
        'inline-flex items-center rounded-lg border font-mono tracking-wide font-medium transition-all shadow-2xs select-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand',
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
