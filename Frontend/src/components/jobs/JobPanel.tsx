import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  RotateCcw,
  Download,
  Ban,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  closeJobDrawer,
  openTitleConfirmModal,
  openReviewModal,
  openTexPreviewModal,
  openJobDrawer,
  setJob,
  setJobs,
} from '@/store/slices/jobsSlice';
import { addToast } from '@/store/slices/uiSlice';
import { useJob } from '@/hooks/useJob';
import { listJobs, createJob } from '@/api/jobs';
import { Button } from '@/components/common/Button';
import { formatDate } from '@/lib/format';
import { JobResponse } from '@/types/api';
import { getErrorMessage } from '@/api/errors';

export const JobPanel: React.FC = () => {
  const dispatch = useAppDispatch();
  const activeJobId = useAppSelector((state) => state.jobs.activeJobDrawerJobId);
  const { job, cancel } = useJob(activeJobId);

  const [history, setHistory] = useState<JobResponse[]>([]);
  const [isCanceling, setIsCanceling] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  // Load history of jobs for this file
  useEffect(() => {
    if (job?.file_id) {
      listJobs({ fileId: job.file_id, limit: 10 })
        .then((res) => {
          const items = res.items || [];
          setHistory(items);
          if (items.length > 0) {
            dispatch(setJobs(items));
          }
        })
        .catch(() => {});
    }
  }, [dispatch, job?.file_id, job?.status]);

  if (!activeJobId || !job) return null;

  const handleClose = () => {
    dispatch(closeJobDrawer());
  };

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel citation generation?')) return;
    setIsCanceling(true);
    try {
      await cancel();
      dispatch(addToast({ type: 'info', message: 'Citation job canceled.' }));
    } catch (err: unknown) {
      dispatch(addToast({ type: 'error', message: getErrorMessage(err) }));
    } finally {
      setIsCanceling(false);
    }
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      const newJob = await createJob(job.file_id, job.tex_mode);
      dispatch(setJob(newJob));
      dispatch(openJobDrawer(newJob.id));
      dispatch(addToast({ type: 'info', message: 'New citation job started.' }));
    } catch (err: unknown) {
      dispatch(addToast({ type: 'error', message: getErrorMessage(err) }));
    } finally {
      setIsRetrying(false);
    }
  };

  const isWaitingTitle = job.status === 'needs_title_confirmation';
  const isWaitingReview = job.status === 'needs_review';
  const isSucceeded = job.status === 'succeeded';
  const isUnresolved = job.status === 'unresolved';
  const isFailed = job.status === 'failed';
  const isCanceled = job.status === 'canceled';
  const isExpired = job.status === 'expired';
  const isActive = job.status === 'queued' || job.status === 'running' || isWaitingTitle || isWaitingReview;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleClose}
          className="fixed inset-0 bg-charcoal-900/40 backdrop-blur-xs"
        />

        <div className="fixed inset-y-0 right-0 max-w-full flex pl-0 sm:pl-10">
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="w-screen max-w-md bg-cream border-l border-border-light shadow-2xl flex flex-col justify-between"
          >
            {/* Header */}
            <div className="p-5 border-b border-border-light bg-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-brand flex items-center justify-center">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-serif text-lg font-bold text-charcoal-900 m-0">
                    Citation Pipeline
                  </h3>
                  <p className="text-[10px] font-mono uppercase tracking-widest text-charcoal/50">
                    Mode: {job.tex_mode} &bull; ID: {job.id.slice(0, 8)}
                  </p>
                </div>
              </div>

              <button
                onClick={handleClose}
                className="p-1.5 rounded-lg text-charcoal/40 hover:text-charcoal hover:bg-cream-200 transition-colors"
                aria-label="Close panel"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* Status Banner */}
              <div className="p-4 rounded-2xl bg-white border border-border-light shadow-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase tracking-wider text-charcoal/50">
                    Status
                  </span>
                  <span className="font-mono text-xs text-charcoal/50">
                    {formatDate(job.created_at)}
                  </span>
                </div>

                <div className="flex items-center gap-2.5 pt-1">
                  {isSucceeded && <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />}
                  {isFailed && <XCircle className="w-5 h-5 text-red-600 shrink-0" />}
                  {isUnresolved && <HelpCircle className="w-5 h-5 text-orange-600 shrink-0" />}
                  {(isWaitingTitle || isWaitingReview) && (
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 animate-pulse" />
                  )}
                  {(job.status === 'queued' || job.status === 'running') && (
                    <div className="w-4 h-4 rounded-full border-2 border-indigo-brand border-t-transparent animate-spin shrink-0" />
                  )}

                  <div className="font-sans font-semibold text-sm text-charcoal-900 capitalize">
                    {job.status.replace(/_/g, ' ')}
                  </div>
                </div>

                {/* State-specific explanatory texts */}
                {isWaitingTitle && (
                  <p className="text-xs text-charcoal/70 font-sans leading-relaxed pt-1">
                    Multiple titles were identified in this document. Please confirm which title should be searched in academic databases.
                  </p>
                )}

                {isWaitingReview && (
                  <p className="text-xs text-charcoal/70 font-sans leading-relaxed pt-1">
                    Bibliographic metadata was retrieved from Crossref/OpenAlex with discrepancies. Please review before compilation.
                  </p>
                )}

                {isSucceeded && (
                  <p className="text-xs text-charcoal/70 font-sans leading-relaxed pt-1">
                    Citation successfully resolved and formatted. Your LaTeX citation is ready to copy or download.
                  </p>
                )}

                {isUnresolved && (
                  <div className="pt-1">
                    <p className="text-xs text-charcoal/70 font-sans leading-relaxed">
                      We could not confirm this paper&rsquo;s details automatically.
                    </p>
                    {job.reasons && job.reasons.length > 0 && (
                      <ul className="mt-2 list-disc list-inside text-[11px] text-charcoal/60 space-y-1">
                        {job.reasons.map((r, i) => (
                          <li key={i}>{String(r)}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {isFailed && (
                  <p className="text-xs text-red-600 font-sans leading-relaxed pt-1">
                    {job.error_code
                      ? `Pipeline encountered an error (${job.error_code}).`
                      : 'An error occurred during extraction. You may try again.'}
                  </p>
                )}

                {(isCanceled || isExpired) && (
                  <p className="text-xs text-charcoal/60 font-sans leading-relaxed pt-1">
                    This job was {job.status}. Start a new job whenever you are ready.
                  </p>
                )}
              </div>

              {/* Action Buttons for current state */}
              <div className="space-y-2">
                {isWaitingTitle && (
                  <Button
                    variant="primary"
                    className="w-full gap-2 shadow-sm"
                    onClick={() => dispatch(openTitleConfirmModal(job.id))}
                  >
                    <AlertTriangle className="w-4 h-4 text-amber-200" />
                    <span>Confirm Paper Title</span>
                  </Button>
                )}

                {isWaitingReview && (
                  <Button
                    variant="primary"
                    className="w-full gap-2 shadow-sm"
                    onClick={() => dispatch(openReviewModal(job.id))}
                  >
                    <AlertTriangle className="w-4 h-4 text-amber-200" />
                    <span>Review Metadata Fields</span>
                  </Button>
                )}

                {isSucceeded && (
                  <Button
                    variant="primary"
                    className="w-full gap-2 shadow-sm"
                    onClick={() => dispatch(openTexPreviewModal(job.id))}
                  >
                    <Download className="w-4 h-4" />
                    <span>Preview & Download .tex</span>
                  </Button>
                )}

                {(isUnresolved || isFailed || isCanceled || isExpired) && (
                  <Button
                    variant="primary"
                    className="w-full gap-2 shadow-sm"
                    onClick={handleRetry}
                    isLoading={isRetrying}
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>Try Again</span>
                  </Button>
                )}

                {isActive && (
                  <Button
                    variant="outline"
                    className="w-full gap-2 text-xs text-red-600 hover:bg-red-50 hover:border-red-200"
                    onClick={handleCancel}
                    isLoading={isCanceling}
                  >
                    <Ban className="w-3.5 h-3.5" />
                    <span>Cancel Job</span>
                  </Button>
                )}
              </div>

              {/* Job Run History */}
              <div className="pt-3">
                <h4 className="font-mono text-xs uppercase tracking-wider text-charcoal/60 font-semibold mb-2.5">
                  Job History for File
                </h4>
                {history.length === 0 ? (
                  <p className="text-xs text-charcoal/40 font-sans">No previous runs.</p>
                ) : (
                  <div className="divide-y divide-border-light rounded-xl border border-border-light bg-white overflow-hidden text-xs">
                    {history.map((h) => (
                      <div
                        key={h.id}
                        onClick={() => {
                          if (h.id !== activeJobId) {
                            dispatch(openJobDrawer(h.id));
                          }
                        }}
                        className={`p-3 flex items-center justify-between cursor-pointer transition-colors ${
                          h.id === activeJobId ? 'bg-indigo-50/70 border-l-2 border-l-indigo-600' : 'hover:bg-cream-100'
                        }`}
                        title="Click to view details for this run"
                      >
                        <div>
                          <div className="font-medium text-charcoal-900 capitalize flex items-center gap-1.5">
                            <span>{h.status.replace(/_/g, ' ')}</span>
                            {h.id === activeJobId && (
                              <span className="text-[9px] font-mono uppercase bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-semibold tracking-wider">
                                Current
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] font-mono text-charcoal/40">
                            {formatDate(h.created_at)} &bull; {h.tex_mode}
                          </div>
                        </div>

                        {h.status === 'succeeded' && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              dispatch(openTexPreviewModal(h.id));
                            }}
                            className="text-xs text-indigo-brand hover:underline font-medium font-mono"
                          >
                            View .tex
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-border-light bg-white text-center text-[11px] font-mono text-charcoal/40 uppercase tracking-widest">
              CiteFlow Automatic Cross-Referencing
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
};
