import React, { useState } from 'react';
import { Sparkles, ChevronRight, X, Loader2, AlertTriangle } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openJobDrawer } from '@/store/slices/jobsSlice';

export const ActiveJobDock: React.FC = () => {
  const dispatch = useAppDispatch();
  const activeDrawerId = useAppSelector((state) => state.jobs.activeJobDrawerJobId);
  const jobsById = useAppSelector((state) => state.jobs.jobsById);
  const isUploadDrawerOpen = useAppSelector((state) => state.upload.isDrawerOpen);

  const [dismissedJobId, setDismissedJobId] = useState<string | null>(null);

  // Find any currently active job
  const activeJobs = React.useMemo(
    () =>
      Object.values(jobsById).filter(
        (job) =>
          ['queued', 'running', 'needs_title_confirmation', 'needs_review'].includes(job.status) &&
          job.id !== dismissedJobId
      ),
    [jobsById, dismissedJobId]
  );

  // If drawer is already open, or no active jobs, do not render
  if (activeDrawerId || activeJobs.length === 0) {
    return null;
  }

  const latestJob = activeJobs[activeJobs.length - 1];
  const isWaiting =
    latestJob.status === 'needs_title_confirmation' || latestJob.status === 'needs_review';

  const positionClass = isUploadDrawerOpen ? 'bottom-24 right-5' : 'bottom-5 right-5';

  return (
    <div
      role="region"
      aria-label="Active Citation Pipeline"
      className={`fixed ${positionClass} z-40 max-w-sm rounded-2xl bg-charcoal-900/95 text-white shadow-2xl border border-charcoal-700/80 backdrop-blur-md p-3 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-3 duration-200`}
    >
      <div className="w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-300 flex items-center justify-center shrink-0">
        {isWaiting ? (
          <AlertTriangle className="w-4 h-4 text-amber-400 animate-pulse" />
        ) : latestJob.status === 'running' ? (
          <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
        ) : (
          <Sparkles className="w-4 h-4 text-indigo-300" />
        )}
      </div>

      <div className="flex-1 min-w-0 pr-1">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-indigo-300 font-semibold">
            Citation Pipeline
          </span>
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        </div>
        <p className="text-xs font-medium text-white truncate">
          {isWaiting ? 'Action required on title/review' : 'Processing document...'}
        </p>
      </div>

      <button
        type="button"
        onClick={() => dispatch(openJobDrawer(latestJob.id))}
        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-brand hover:bg-indigo-hover text-white text-xs font-medium transition-colors cursor-pointer shrink-0"
      >
        <span>View</span>
        <ChevronRight className="w-3.5 h-3.5" />
      </button>

      <button
        type="button"
        onClick={() => setDismissedJobId(latestJob.id)}
        aria-label="Dismiss notification"
        className="p-1 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
