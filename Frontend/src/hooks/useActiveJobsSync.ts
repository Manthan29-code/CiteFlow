import { useEffect, useRef, useCallback, useMemo } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setJobs } from '@/store/slices/jobsSlice';
import { listJobs } from '@/api/jobs';
import { env } from '@/lib/env';

/**
 * Hook to reactively synchronize active/in-progress citation jobs across the application.
 *
 * Features:
 * - Reactive Polling: Only runs when at least one job is 'queued' or 'running' (or starting).
 * - Pauses when tab is hidden to save network/CPU resources.
 * - Triggers an instant refresh when switching back to CiteFlow (window.focus / visibilitychange).
 * - Stops completely once all jobs reach terminal states (succeeded, unresolved, failed, etc.)
 *   or user-review states (needs_review, needs_title_confirmation).
 */
export function useActiveJobsSync() {
  const dispatch = useAppDispatch();
  const jobsById = useAppSelector((state) => state.jobs.jobsById);
  const isStartingJobByFileId = useAppSelector((state) => state.jobs.isStartingJobByFileId);

  // Determine if any jobs are currently in-flight
  const hasActiveJobs = useMemo(() => {
    const hasStarting = Object.values(isStartingJobByFileId).some(Boolean);
    if (hasStarting) return true;
    return Object.values(jobsById).some(
      (job) => job.status === 'queued' || job.status === 'running'
    );
  }, [jobsById, isStartingJobByFileId]);

  const isFetchingRef = useRef<boolean>(false);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch updated jobs from backend and dispatch into Redux
  const fetchJobs = useCallback(async () => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;
    try {
      const res = await listJobs({ limit: 200 });
      if (res.items && res.items.length > 0) {
        dispatch(setJobs(res.items));
      }
    } catch {
      // Background sync errors are silenced to avoid intrusive UI popups
    } finally {
      isFetchingRef.current = false;
    }
  }, [dispatch]);

  // Periodic polling only while active jobs exist
  useEffect(() => {
    if (!hasActiveJobs) {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      return;
    }

    const intervalMs = env.VITE_ACTIVE_JOBS_POLL_INTERVAL_MS || 8000;

    pollTimerRef.current = setInterval(() => {
      // Pause polling if the tab is hidden to prevent unnecessary background traffic
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
        return;
      }
      fetchJobs();
    }, intervalMs);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [hasActiveJobs, fetchJobs]);

  // Instant refresh when user switches back to CiteFlow
  useEffect(() => {
    const handleFocusOrVisible = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
        if (hasActiveJobs) {
          fetchJobs();
        }
      }
    };

    window.addEventListener('focus', handleFocusOrVisible);
    document.addEventListener('visibilitychange', handleFocusOrVisible);

    return () => {
      window.removeEventListener('focus', handleFocusOrVisible);
      document.removeEventListener('visibilitychange', handleFocusOrVisible);
    };
  }, [hasActiveJobs, fetchJobs]);

  return {
    hasActiveJobs,
    syncNow: fetchJobs,
  };
}
