import React, { useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeTitleConfirmModal } from '@/store/slices/jobsSlice';
import { addToast } from '@/store/slices/uiSlice';
import { useJob } from '@/hooks/useJob';
import { Modal } from '@/components/common/Modal';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import { ConfirmTitleInterrupt, ConfirmTitleCandidate } from '@/types/api';
import { ApiError, getErrorMessage } from '@/api/errors';

export const TitleConfirmDialog: React.FC = () => {
  const dispatch = useAppDispatch();
  const activeJobId = useAppSelector((state) => state.jobs.activeTitleConfirmJobId);
  const { job, resume, refetch } = useJob(activeJobId);

  const [selectedOption, setSelectedOption] = useState<number | 'custom' | null>(null);
  const [customTitle, setCustomTitle] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const pending = job?.pending_interrupt as ConfirmTitleInterrupt | undefined;
  const candidates: ConfirmTitleCandidate[] = pending?.candidates || [];
  const currentChoice = selectedOption !== null ? selectedOption : (candidates.length > 0 ? 0 : 'custom');

  const handleClose = () => {
    setError(null);
    setSelectedOption(null);
    dispatch(closeTitleConfirmModal());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!job) return;

    setError(null);

    if (currentChoice === 'custom') {
      const trimmed = customTitle.trim();
      if (!trimmed) {
        setError('Please enter a title or choose one from the list.');
        return;
      }
      if (trimmed.length > 300) {
        setError('Title must be 300 characters or fewer.');
        return;
      }
      // eslint-disable-next-line no-control-regex
      if (/[/\\:\0\x00-\x1F\x7F]/.test(trimmed)) {
        setError('Title contains invalid characters.');
        return;
      }

      setIsSubmitting(true);
      try {
        await resume({ action: 'custom', title: trimmed });
        dispatch(
          addToast({
            type: 'success',
            message: 'Custom title submitted. Continuing citation pipeline...',
          })
        );
        handleClose();
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 409) {
          await refetch();
          dispatch(
            addToast({
              type: 'info',
              message: "This file's status changed.",
            })
          );
          handleClose();
        } else {
          setError(getErrorMessage(err));
        }
      } finally {
        setIsSubmitting(false);
      }
    } else {
      // Radio selection
      const index = Number(currentChoice);
      setIsSubmitting(true);
      try {
        await resume({ action: 'select', index });
        dispatch(
          addToast({
            type: 'success',
            message: 'Title confirmed. Continuing citation pipeline...',
          })
        );
        handleClose();
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 409) {
          await refetch();
          dispatch(
            addToast({
              type: 'info',
              message: "This file's status changed.",
            })
          );
          handleClose();
        } else {
          setError(getErrorMessage(err));
        }
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleSkip = async () => {
    if (!job) return;
    setIsSubmitting(true);
    try {
      await resume({ action: 'skip' });
      dispatch(
        addToast({
          type: 'info',
          message: 'Title confirmation skipped.',
        })
      );
      handleClose();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const getCandidateText = (c: ConfirmTitleCandidate) => c.title || c.text || 'Untitled Candidate';

  const getConfidenceBadge = (c: ConfirmTitleCandidate) => {
    const score = c.score !== undefined ? Math.round(c.score * 100) : null;
    const confidence =
      c.confidence || (score !== null && score >= 85 ? 'high' : score !== null && score >= 60 ? 'medium' : 'low');

    const colors = {
      high: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      medium: 'bg-amber-50 text-amber-800 border-amber-200',
      low: 'bg-charcoal/5 text-charcoal/60 border-border-light',
    };

    return (
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono border uppercase tracking-wider ${colors[confidence]}`}>
        {score !== null ? `${score}% Match` : `${confidence} confidence`}
      </span>
    );
  };

  return (
    <Modal
      isOpen={!!activeJobId}
      onClose={handleClose}
      title="Confirm Paper Title"
      description="Select the accurate title for this document to locate official cross-references."
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-sans" role="alert">
            {error}
          </div>
        )}

        <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
          {candidates.map((cand, idx) => {
            const isChecked = currentChoice === idx;
            const candText = getCandidateText(cand);

            return (
              <label
                key={idx}
                className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                  isChecked
                    ? 'border-indigo-brand bg-indigo-50/50 shadow-xs'
                    : 'border-border-light hover:bg-cream-200/60'
                }`}
              >
                <input
                  type="radio"
                  name="title-option"
                  checked={isChecked}
                  onChange={() => setSelectedOption(idx)}
                  disabled={isSubmitting}
                  className="mt-1 w-4 h-4 text-indigo-brand focus:ring-indigo-brand accent-indigo-brand cursor-pointer"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {getConfidenceBadge(cand)}
                    {cand.source && (
                      <span className="text-[10px] font-mono text-charcoal/40 uppercase">
                        Source: {cand.source}
                      </span>
                    )}
                  </div>
                  <div className="text-xs sm:text-sm font-sans font-medium text-charcoal-900 leading-snug">
                    {candText}
                  </div>
                </div>
              </label>
            );
          })}

          {/* Option: Custom title */}
          <label
            className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
              currentChoice === 'custom'
                ? 'border-indigo-brand bg-indigo-50/50 shadow-xs'
                : 'border-border-light hover:bg-cream-200/60'
            }`}
          >
            <input
              type="radio"
              name="title-option"
              checked={currentChoice === 'custom'}
              onChange={() => setSelectedOption('custom')}
              disabled={isSubmitting}
              className="mt-1 w-4 h-4 text-indigo-brand focus:ring-indigo-brand accent-indigo-brand cursor-pointer"
            />
            <div className="flex-1 min-w-0">
              <div className="text-xs sm:text-sm font-sans font-medium text-charcoal-900">
                Type the title manually
              </div>
              <div className="text-[11px] text-charcoal/50">
                If the detected titles above are incomplete or inaccurate
              </div>
            </div>
          </label>
        </div>

        {/* Custom title input if selected */}
        {selectedOption === 'custom' && (
          <div className="pt-2 animate-in fade-in duration-150">
            <Input
              label="Custom Document Title"
              placeholder="e.g. Attention Is All You Need"
              value={customTitle}
              onChange={(e) => {
                setCustomTitle(e.target.value);
                if (error) setError(null);
              }}
              autoFocus
              disabled={isSubmitting}
              helperText="1 to 300 characters, no control characters."
            />
          </div>
        )}

        <div className="flex items-center justify-between pt-4 border-t border-border-light">
          <Button
            type="button"
            variant="ghost"
            onClick={handleSkip}
            disabled={isSubmitting}
            className="text-xs text-charcoal/60 hover:text-charcoal font-mono"
          >
            Skip this file
          </Button>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
            >
              Confirm Title
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
};
