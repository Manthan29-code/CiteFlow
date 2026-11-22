import React from 'react';
import { FileText, Loader2 } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setJob, setStartingJob, openJobDrawer } from '@/store/slices/jobsSlice';
import { addToast, openStyleManagerModal } from '@/store/slices/uiSlice';
import { createJob } from '@/api/jobs';
import { ApiError, getErrorMessage } from '@/api/errors';
import { cn } from '@/lib/utils';

export interface GenerateButtonProps {
  fileId: string;
  fileName: string;
  disabled?: boolean;
  className?: string;
  iconOnly?: boolean;
}

export const GenerateButton: React.FC<GenerateButtonProps> = ({
  fileId,
  fileName,
  disabled = false,
  className,
  iconOnly = false,
}) => {
  const dispatch = useAppDispatch();
  const isStarting = useAppSelector((state) => state.jobs.isStartingJobByFileId[fileId] || false);
  const { styles, selectedStyleId } = useAppSelector((state) => state.styles);

  const handleStartJob = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isStarting || disabled) return;

    if (styles.length === 0) {
      dispatch(
        addToast({
          type: 'error',
          message: "You can't generate citations without any citation style. Please add a style first.",
        })
      );
      dispatch(openStyleManagerModal());
      return;
    }

    // Immediately disable button to prevent double clicks
    dispatch(setStartingJob({ fileId, isStarting: true }));

    try {
      const job = await createJob(fileId, 'fragment', selectedStyleId);
      dispatch(setJob(job));
      dispatch(openJobDrawer(job.id));
      dispatch(
        addToast({
          type: 'info',
          message: `Citation job started for "${fileName}".`,
        })
      );
    } catch (err: unknown) {
      if (err instanceof ApiError && err.code === 'too_many_active_jobs') {
        dispatch(
          addToast({
            type: 'error',
            message: 'You have too many files processing. Wait for one to finish.',
          })
        );
      } else {
        dispatch(
          addToast({
            type: 'error',
            message: `Could not start citation generation: ${getErrorMessage(err)}`,
          })
        );
      }
    } finally {
      dispatch(setStartingJob({ fileId, isStarting: false }));
    }
  };

  if (iconOnly) {
    return (
      <button
        type="button"
        onClick={handleStartJob}
        disabled={disabled || isStarting}
        title="Generate citation"
        aria-label="Generate citation"
        className={cn(
          'inline-flex items-center justify-center w-6 h-6 rounded-md bg-indigo-brand text-white shadow-xs transition-all',
          'hover:bg-indigo-hover active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand',
          className
        )}
      >
        {isStarting ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <FileText className="w-3.5 h-3.5" />
        )}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleStartJob}
      disabled={disabled || isStarting}
      title="Generate citation"
      aria-label="Generate citation"
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-semibold text-white rounded-xl bg-indigo-brand shadow-xs transition-all',
        'hover:bg-indigo-hover active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand',
        className
      )}
    >
      {isStarting ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
      ) : (
        <FileText className="w-3.5 h-3.5 shrink-0" />
      )}
      <span className="font-mono text-xs font-semibold">
        {isStarting ? 'Starting...' : 'Generate'}
      </span>
    </button>
  );
};
