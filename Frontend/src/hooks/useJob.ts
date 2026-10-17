import { useEffect, useRef, useCallback, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setJob, openTitleConfirmModal, openReviewModal } from '@/store/slices/jobsSlice';
import { getJobDetail, resumeJob, cancelJob, streamJobEvents } from '@/api/jobs';
import { JobResponse, ResumeRequest } from '@/types/api';
import { env } from '@/lib/env';

export function useJob(jobId: string | null) {
  const dispatch = useAppDispatch();
  const job = useAppSelector((state) => (jobId ? state.jobs.jobsById[jobId] : undefined));

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentIntervalRef = useRef<number>(env.VITE_JOB_POLL_INTERVAL_MS);
  const lastStatusRef = useRef<string | null>(job?.status || null);
  const sseUnsubRef = useRef<(() => void) | null>(null);

  // Fetch job status and update Redux store
  const fetchStatus = useCallback(async (): Promise<JobResponse | null> => {
    if (!jobId) return null;
    try {
      const data = await getJobDetail(jobId);
      dispatch(setJob(data));
      return data;
    } catch {
      return null;
    }
  }, [jobId, dispatch]);

  // Main polling & SSE loop
  useEffect(() => {
    if (!jobId) return;

    let isMounted = true;

    const stopPolling = () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };

    const scheduleNextPoll = (intervalMs: number) => {
      stopPolling();
      pollTimerRef.current = setTimeout(async () => {
        if (!isMounted) return;

        // Skip polling if document is hidden, will refetch on focus
        if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
          return;
        }

        const updated = await fetchStatus();
        if (!updated || !isMounted) return;

        const isTerminal = ['succeeded', 'unresolved', 'failed', 'canceled', 'expired'].includes(updated.status);
        const isWaitingForUser = ['needs_title_confirmation', 'needs_review'].includes(updated.status);

        if (isTerminal || isWaitingForUser) {
          stopPolling();

          // Auto-prompt modal if waiting for user
          if (updated.status === 'needs_title_confirmation') {
            dispatch(openTitleConfirmModal(updated.id));
          } else if (updated.status === 'needs_review') {
            dispatch(openReviewModal(updated.id));
          }
          return;
        }

        // Back off interval if status hasn't changed
        if (updated.status === lastStatusRef.current) {
          currentIntervalRef.current = Math.min(
            env.VITE_JOB_POLL_MAX_INTERVAL_MS,
            Math.round(currentIntervalRef.current * 1.5)
          );
        } else {
          currentIntervalRef.current = env.VITE_JOB_POLL_INTERVAL_MS;
          lastStatusRef.current = updated.status;
        }

        scheduleNextPoll(currentIntervalRef.current);
      }, intervalMs);
    };

    // If SSE is enabled, try SSE first, fall back to polling
    if (env.VITE_ENABLE_SSE) {
      sseUnsubRef.current = streamJobEvents(
        jobId,
        (sseJob) => {
          if (!isMounted) return;
          dispatch(setJob(sseJob));
          if (sseJob.status === 'needs_title_confirmation') {
            dispatch(openTitleConfirmModal(sseJob.id));
          } else if (sseJob.status === 'needs_review') {
            dispatch(openReviewModal(sseJob.id));
          }
        },
        () => {
          // SSE failed: fall back to polling
          if (isMounted) {
            scheduleNextPoll(env.VITE_JOB_POLL_INTERVAL_MS);
          }
        }
      );
    } else {
      // Immediate status check, then start polling
      fetchStatus().then((initialJob) => {
        if (!initialJob || !isMounted) return;
        lastStatusRef.current = initialJob.status;

        const isTerminal = ['succeeded', 'unresolved', 'failed', 'canceled', 'expired'].includes(initialJob.status);
        const isWaiting = ['needs_title_confirmation', 'needs_review'].includes(initialJob.status);

        if (!isTerminal && !isWaiting) {
          scheduleNextPoll(env.VITE_JOB_POLL_INTERVAL_MS);
        } else if (isWaiting) {
          if (initialJob.status === 'needs_title_confirmation') {
            dispatch(openTitleConfirmModal(initialJob.id));
          } else {
            dispatch(openReviewModal(initialJob.id));
          }
        }
      });
    }

    // Window focus listener: refetch when tab becomes visible again
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isMounted) {
        fetchStatus().then((j) => {
          if (j && (j.status === 'queued' || j.status === 'running')) {
            currentIntervalRef.current = env.VITE_JOB_POLL_INTERVAL_MS;
            scheduleNextPoll(currentIntervalRef.current);
          }
        });
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isMounted = false;
      stopPolling();
      if (sseUnsubRef.current) {
        sseUnsubRef.current();
        sseUnsubRef.current = null;
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [jobId, dispatch, fetchStatus]);

  // Action: Resume Job
  const resume = useCallback(
    async (payload: ResumeRequest) => {
      if (!jobId) return null;
      setIsLoading(true);
      setError(null);
      try {
        const updated = await resumeJob(jobId, payload);
        dispatch(setJob(updated));
        // Reset polling interval back to baseline
        currentIntervalRef.current = env.VITE_JOB_POLL_INTERVAL_MS;
        lastStatusRef.current = updated.status;
        return updated;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to resume job';
        setError(msg);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [jobId, dispatch]
  );

  // Action: Cancel Job
  const cancel = useCallback(async () => {
    if (!jobId) return null;
    setIsLoading(true);
    setError(null);
    try {
      const updated = await cancelJob(jobId);
      dispatch(setJob(updated));
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to cancel job';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [jobId, dispatch]);

  return {
    job,
    isLoading,
    error,
    refetch: fetchStatus,
    resume,
    cancel,
  };
}
