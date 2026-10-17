import React, { useState } from 'react';
import {
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeReviewModal } from '@/store/slices/jobsSlice';
import { addToast } from '@/store/slices/uiSlice';
import { useJob } from '@/hooks/useJob';
import { Modal } from '@/components/common/Modal';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import { ReviewInterrupt, ReviewAuthor } from '@/types/api';
import { ApiError, getErrorMessage } from '@/api/errors';

interface ReviewFormInnerProps {
  jobId: string;
}

const ReviewFormInner: React.FC<ReviewFormInnerProps> = ({ jobId }) => {
  const dispatch = useAppDispatch();
  const { job, resume, refetch } = useJob(jobId);

  const pending = job?.pending_interrupt as ReviewInterrupt | undefined;
  const initialRecord = (pending?.record || {}) as Record<string, unknown>;

  // Form states initialized directly from initialRecord
  const [title, setTitle] = useState(() => (initialRecord.title as string) || '');
  const [year, setYear] = useState(() =>
    initialRecord.year !== undefined && initialRecord.year !== null ? String(initialRecord.year) : ''
  );
  const [journal, setJournal] = useState(() => (initialRecord.journal as string) || '');
  const [journalAbbr, setJournalAbbr] = useState(() => (initialRecord.journal_abbreviation as string) || '');
  const [doiUrl, setDoiUrl] = useState(() => (initialRecord.doi_url as string) || '');
  const [volume, setVolume] = useState(() => (initialRecord.volume as string) || '');
  const [issue, setIssue] = useState(() => (initialRecord.issue as string) || '');
  const [firstPage, setFirstPage] = useState(() => (initialRecord.first_page as string) || '');
  const [articleNumber, setArticleNumber] = useState(() => (initialRecord.article_number as string) || '');

  const [authors, setAuthors] = useState<ReviewAuthor[]>(() => {
    const rawAuthors = (initialRecord.authors || []) as unknown[];
    const parsed: ReviewAuthor[] = rawAuthors.map((a) => {
      if (typeof a === 'string') {
        const parts = a.split(' ');
        return {
          surname: parts[parts.length - 1] || '',
          given_name: parts.slice(0, -1).join(' ') || '',
        };
      } else if (typeof a === 'object' && a !== null) {
        const obj = a as Record<string, string>;
        return {
          surname: obj.surname || obj.last_name || '',
          given_name: obj.given_name || obj.first_name || '',
          middle_name: obj.middle_name || '',
        };
      }
      return { surname: '', given_name: '' };
    });
    return parsed.length > 0 ? parsed : [{ surname: '', given_name: '' }];
  });

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleClose = () => {
    setGeneralError(null);
    setFieldErrors({});
    dispatch(closeReviewModal());
  };

  // Author List manipulations
  const handleAddAuthor = () => {
    setAuthors([...authors, { surname: '', given_name: '', middle_name: '' }]);
  };

  const handleRemoveAuthor = (index: number) => {
    setAuthors(authors.filter((_, i) => i !== index));
  };

  const handleAuthorChange = (index: number, field: keyof ReviewAuthor, val: string) => {
    const updated = [...authors];
    updated[index] = { ...updated[index], [field]: val };
    setAuthors(updated);
  };

  const handleMoveAuthor = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === authors.length - 1) return;

    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    const updated = [...authors];
    const [moved] = updated.splice(index, 1);
    updated.splice(targetIdx, 0, moved);
    setAuthors(updated);
  };

  // Resolve conflict button
  const handleApplyConflictValue = (field: string, value: unknown) => {
    if (field === 'year') setYear(String(value));
    if (field === 'journal') setJournal(String(value));
    if (field === 'journal_abbreviation') setJournalAbbr(String(value));
    if (field === 'title') setTitle(String(value));
    if (field === 'doi_url') setDoiUrl(String(value));
  };

  // Action: Accept as is
  const handleAcceptAsIs = async () => {
    if (!job) return;
    setIsSubmitting(true);
    try {
      await resume({ action: 'accept' });
      dispatch(
        addToast({
          type: 'success',
          message: 'Metadata accepted as is. Proceeding to format citation...',
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
        setGeneralError(getErrorMessage(err));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Action: Save changes and continue (only sends modified fields)
  const handleSaveEdits = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!job) return;

    setFieldErrors({});
    setGeneralError(null);

    // Validate year
    const errors: Record<string, string> = {};
    const nextYear = new Date().getFullYear() + 1;
    if (year.trim()) {
      const yNum = parseInt(year.trim(), 10);
      if (isNaN(yNum) || yNum < 1000 || yNum > nextYear) {
        errors.year = `Year must be an integer between 1000 and ${nextYear}.`;
      }
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    // Determine changed fields only
    const edits: Record<string, unknown> = {};

    if (title.trim() !== ((initialRecord.title as string) || '')) {
      edits.title = title.trim();
    }
    if (journal.trim() !== ((initialRecord.journal as string) || '')) {
      edits.journal = journal.trim();
    }
    if (journalAbbr.trim() !== ((initialRecord.journal_abbreviation as string) || '')) {
      edits.journal_abbreviation = journalAbbr.trim();
    }
    if (doiUrl.trim() !== ((initialRecord.doi_url as string) || '')) {
      edits.doi_url = doiUrl.trim();
    }
    if (volume.trim() !== ((initialRecord.volume as string) || '')) {
      edits.volume = volume.trim();
    }
    if (issue.trim() !== ((initialRecord.issue as string) || '')) {
      edits.issue = issue.trim();
    }
    if (firstPage.trim() !== ((initialRecord.first_page as string) || '')) {
      edits.first_page = firstPage.trim();
    }
    if (articleNumber.trim() !== ((initialRecord.article_number as string) || '')) {
      edits.article_number = articleNumber.trim();
    }
    if (
      year.trim() !==
      (initialRecord.year !== undefined && initialRecord.year !== null ? String(initialRecord.year) : '')
    ) {
      edits.year = year.trim() ? parseInt(year.trim(), 10) : null;
    }

    const cleanAuthors = authors
      .map((a) => [a.given_name, a.middle_name, a.surname].filter(Boolean).join(' ').trim())
      .filter(Boolean);

    edits.authors = cleanAuthors;

    if (Object.keys(edits).length === 0) {
      return handleAcceptAsIs();
    }

    setIsSubmitting(true);
    try {
      await resume({ action: 'edit', edits });
      dispatch(
        addToast({
          type: 'success',
          message: 'Saved metadata edits. Re-validating citation...',
        })
      );
      handleClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          await refetch();
          dispatch(addToast({ type: 'info', message: "This file's status changed." }));
          handleClose();
        } else if (err.status === 422 && err.details) {
          const mapped: Record<string, string> = {};
          Object.entries(err.details).forEach(([k, v]) => {
            mapped[k] = String(v);
          });
          setFieldErrors(mapped);
          setGeneralError('Please correct the highlighted fields.');
        } else {
          setGeneralError(getErrorMessage(err));
        }
      } else {
        setGeneralError(getErrorMessage(err));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = async () => {
    if (!job) return;
    setIsSubmitting(true);
    try {
      await resume({ action: 'skip' });
      dispatch(addToast({ type: 'info', message: 'Metadata review skipped.' }));
      handleClose();
    } catch (err: unknown) {
      setGeneralError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const conflicts = pending?.conflicts || [];
  const warnings = pending?.warnings || [];

  return (
    <Modal
      isOpen={true}
      onClose={handleClose}
      title="Review Citation Metadata"
      description="Inspect cross-referenced metadata before generating your LaTeX citation document."
      maxWidth="xl"
    >
      <form onSubmit={handleSaveEdits} className="space-y-5">
        {generalError && (
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-sans" role="alert">
            {generalError}
          </div>
        )}

        {/* Warnings list */}
        {warnings.length > 0 && (
          <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 space-y-1.5 text-xs text-amber-900">
            <div className="flex items-center gap-1.5 font-semibold font-mono uppercase tracking-wider text-[11px]">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              <span>Pipeline Notice</span>
            </div>
            {warnings.map((w, idx) => (
              <p key={idx} className="font-sans pl-5 leading-relaxed">{w}</p>
            ))}
          </div>
        )}

        {/* Conflicts Box */}
        {conflicts.length > 0 && (
          <div className="p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-200 text-xs space-y-2">
            <div className="font-mono uppercase tracking-wider text-[11px] font-semibold text-indigo-950 flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-indigo-brand" />
              <span>Source Discrepancies</span>
            </div>
            {conflicts.map((conf, idx) => (
              <div key={idx} className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-lg bg-white border border-indigo-100">
                <span className="font-mono text-charcoal/70 uppercase text-[11px]">
                  {conf.field}:
                </span>
                <div className="flex items-center gap-2">
                  {conf.crossref_val !== undefined && (
                    <button
                      type="button"
                      onClick={() => handleApplyConflictValue(conf.field, conf.crossref_val)}
                      className="px-2 py-0.5 rounded text-[11px] bg-cream-200 hover:bg-indigo-100 text-charcoal-900 font-mono transition-colors"
                    >
                      Crossref: {String(conf.crossref_val)} &rarr; Use
                    </button>
                  )}
                  {conf.openalex_val !== undefined && (
                    <button
                      type="button"
                      onClick={() => handleApplyConflictValue(conf.field, conf.openalex_val)}
                      className="px-2 py-0.5 rounded text-[11px] bg-cream-200 hover:bg-indigo-100 text-charcoal-900 font-mono transition-colors"
                    >
                      OpenAlex: {String(conf.openalex_val)} &rarr; Use
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Scrollable Fields Grid */}
        <div className="max-h-96 overflow-y-auto space-y-4 pr-1">
          {/* Document Title */}
          <Input
            label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            error={fieldErrors.title}
            disabled={isSubmitting}
          />

          {/* Authors Editor */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-mono tracking-wide uppercase text-charcoal/80 font-medium">
                Authors ({authors.length})
              </label>
              <button
                type="button"
                onClick={handleAddAuthor}
                className="inline-flex items-center gap-1 text-[11px] font-mono uppercase text-indigo-brand hover:underline font-semibold"
              >
                <Plus className="w-3 h-3" />
                <span>Add Author</span>
              </button>
            </div>

            <div className="space-y-2">
              {authors.map((author, index) => (
                <div key={index} className="flex items-center gap-2 p-2 rounded-xl bg-white border border-border-light shadow-2xs">
                  <span className="text-xs font-mono text-charcoal/40 w-4 text-center">
                    {index + 1}
                  </span>
                  <input
                    type="text"
                    placeholder="Given / First Name"
                    value={author.given_name || ''}
                    onChange={(e) => handleAuthorChange(index, 'given_name', e.target.value)}
                    className="flex-1 px-2.5 py-1.5 text-xs bg-cream-50 border border-border-light rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-brand"
                  />
                  <input
                    type="text"
                    placeholder="Surname / Last Name"
                    value={author.surname || ''}
                    onChange={(e) => handleAuthorChange(index, 'surname', e.target.value)}
                    className="flex-1 px-2.5 py-1.5 text-xs bg-cream-50 border border-border-light rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-brand font-medium"
                  />
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleMoveAuthor(index, 'up')}
                      disabled={index === 0}
                      className="p-1 rounded text-charcoal/40 hover:text-charcoal disabled:opacity-20"
                      title="Move author up"
                    >
                      <ArrowUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleMoveAuthor(index, 'down')}
                      disabled={index === authors.length - 1}
                      className="p-1 rounded text-charcoal/40 hover:text-charcoal disabled:opacity-20"
                      title="Move author down"
                    >
                      <ArrowDown className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemoveAuthor(index)}
                      className="p-1 rounded text-charcoal/40 hover:text-red-600 transition-colors"
                      title="Remove author"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-charcoal/50 font-sans">
              Rule: 7 or fewer authors are listed in full. More than 7 will output the first author followed by &ldquo;et al.&rdquo;
            </p>
          </div>

          {/* Journal & Abbreviation */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Journal / Venue"
              value={journal}
              onChange={(e) => setJournal(e.target.value)}
              error={fieldErrors.journal}
              disabled={isSubmitting}
            />
            <Input
              label="Journal Abbreviation"
              placeholder="e.g. NeurIPS"
              value={journalAbbr}
              onChange={(e) => setJournalAbbr(e.target.value)}
              error={fieldErrors.journal_abbreviation}
              disabled={isSubmitting}
            />
          </div>

          {/* Year & DOI */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Input
              label="Publication Year"
              type="number"
              placeholder="e.g. 2017"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              error={fieldErrors.year}
              disabled={isSubmitting}
            />
            <div className="sm:col-span-2">
              <Input
                label="DOI URL"
                placeholder="https://doi.org/10.xxxx/..."
                value={doiUrl}
                onChange={(e) => setDoiUrl(e.target.value)}
                error={fieldErrors.doi_url}
                disabled={isSubmitting}
              />
            </div>
          </div>

          {/* Volume, Issue, Pages, Article Number */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Input
              label="Volume"
              placeholder="e.g. 30"
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label="Issue"
              placeholder="e.g. 4"
              value={issue}
              onChange={(e) => setIssue(e.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label="First Page"
              placeholder="e.g. 5998"
              value={firstPage}
              onChange={(e) => setFirstPage(e.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label="Article No."
              placeholder="e.g. e12345"
              value={articleNumber}
              onChange={(e) => setArticleNumber(e.target.value)}
              disabled={isSubmitting}
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-4 border-t border-border-light">
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
              onClick={handleAcceptAsIs}
              disabled={isSubmitting}
              className="gap-1.5"
            >
              <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
              <span>Accept As Is</span>
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
            >
              Save & Continue
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
};

export const ReviewFormDialog: React.FC = () => {
  const activeJobId = useAppSelector((state) => state.jobs.activeReviewJobId);
  if (!activeJobId) return null;

  return <ReviewFormInner key={activeJobId} jobId={activeJobId} />;
};
