import React, { useState, useMemo } from 'react';
import {
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Edit3,
  Copy,
  Check,
  ListFilter,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeReviewModal } from '@/store/slices/jobsSlice';
import { addToast } from '@/store/slices/uiSlice';
import { useJob } from '@/hooks/useJob';
import { Modal } from '@/components/common/Modal';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import { ReviewInterrupt, ReviewAuthor, ReviewConflict } from '@/types/api';
import { ApiError, getErrorMessage } from '@/api/errors';

interface ReviewFormInnerProps {
  jobId: string;
}

type ConflictChoice = 'crossref' | 'openalex' | 'custom';

interface ResolutionItem {
  choice: ConflictChoice;
  customValue: string;
}

export const ReviewFormInner: React.FC<ReviewFormInnerProps> = ({ jobId }) => {
  const dispatch = useAppDispatch();
  const { job, resume, refetch } = useJob(jobId);

  const pending = job?.pending_interrupt as ReviewInterrupt | undefined;

  // Correctly extract initial metadata from selected_metadata (fallback to record)
  const initialRecord = useMemo(() => {
    return (pending?.selected_metadata || pending?.record || {}) as Record<string, unknown>;
  }, [pending]);

  const conflicts = useMemo(() => {
    return (pending?.conflicts || []) as ReviewConflict[];
  }, [pending]);

  const warnings = useMemo(() => {
    return pending?.warnings || pending?.validation_errors || [];
  }, [pending]);

  // Mode: if there are conflicts, default to 'wizard', otherwise 'full_form'
  const [viewMode, setViewMode] = useState<'wizard' | 'full_form'>(() =>
    conflicts.length > 0 ? 'wizard' : 'full_form'
  );

  const [currentConflictIdx, setCurrentConflictIdx] = useState(0);

  // Map of field -> resolution decision
  const [resolutions, setResolutions] = useState<Record<string, ResolutionItem>>(() => {
    const initial: Record<string, ResolutionItem> = {};
    return initial;
  });

  // Full form editable state (initialized from initialRecord)
  const [title, setTitle] = useState(() => (initialRecord.title as string) || '');
  const [year, setYear] = useState(() =>
    initialRecord.year !== undefined && initialRecord.year !== null ? String(initialRecord.year) : ''
  );
  const [journal, setJournal] = useState(() => (initialRecord.journal as string) || '');
  const [journalAbbr, setJournalAbbr] = useState(
    () => (initialRecord.journal_abbreviation as string) || ''
  );
  const [doiUrl, setDoiUrl] = useState(() => (initialRecord.doi_url as string) || '');
  const [volume, setVolume] = useState(() => (initialRecord.volume as string) || '');
  const [issue, setIssue] = useState(() => (initialRecord.issue as string) || '');
  const [firstPage, setFirstPage] = useState(() => (initialRecord.first_page as string) || '');
  const [articleNumber, setArticleNumber] = useState(
    () => (initialRecord.article_number as string) || ''
  );

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
  const [validationWarning, setValidationWarning] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleClose = () => {
    setGeneralError(null);
    setValidationWarning(null);
    setFieldErrors({});
    dispatch(closeReviewModal());
  };

  // Helper to extract values from a conflict
  const getCrossrefVal = (conf: ReviewConflict): unknown => {
    if (conf.crossref !== undefined) return conf.crossref;
    if (conf.crossref_val !== undefined) return conf.crossref_val;
    if (conf.crossref_title !== undefined) return conf.crossref_title;
    if (conf.candidate_options?.[0]) return conf.candidate_options[0];
    return undefined;
  };

  const getOpenalexVal = (conf: ReviewConflict): unknown => {
    if (conf.openalex !== undefined) return conf.openalex;
    if (conf.openalex_val !== undefined) return conf.openalex_val;
    if (conf.openalex_title !== undefined) return conf.openalex_title;
    if (conf.candidate_options?.[1]) return conf.candidate_options[1];
    return undefined;
  };

  // Formats value into human-readable text
  const formatDisplayValue = (val: unknown): string => {
    if (val === undefined || val === null) return '—';
    if (typeof val === 'string') return val;
    if (typeof val === 'number') return String(val);
    if (typeof val === 'boolean') return val ? 'Yes' : 'No';

    if (Array.isArray(val)) {
      if (val.length === 0) return 'No items listed';
      return val
        .map((item) => {
          if (typeof item === 'string') return item;
          if (typeof item === 'object' && item !== null) {
            const auth = item as Record<string, string>;
            const surname = auth.surname || auth.last_name || '';
            const given = auth.given_name || auth.first_name || '';
            if (surname && given) return `${surname}, ${given}`;
            return surname || given || auth.name || '';
          }
          return String(item);
        })
        .filter(Boolean)
        .join('; ');
    }

    if (typeof val === 'object') {
      const obj = val as Record<string, unknown>;
      if (obj.title) {
        const y = obj.year ? ` (${obj.year})` : '';
        const j = obj.journal ? ` — ${obj.journal}` : '';
        return `${obj.title}${y}${j}`;
      }
      return JSON.stringify(val);
    }

    return String(val);
  };

  // Convert custom text into structured value for edits payload
  const parseCustomValue = (field: string, text: string): unknown => {
    const trimmed = text.trim();
    if (field === 'year') {
      const num = parseInt(trimmed, 10);
      return isNaN(num) ? trimmed : num;
    }
    if (field === 'is_preprint') {
      return trimmed.toLowerCase() === 'true' || trimmed.toLowerCase() === 'yes';
    }
    if (field === 'authors') {
      const parts = trimmed.split(/;|\n/).filter(Boolean);
      const authorList = (parts.length > 1 ? parts : trimmed.split(',')).map((p) => p.trim()).filter(Boolean);
      return authorList.map((aStr) => {
        const pieces = aStr.split(/\s+/);
        if (pieces.length === 1) return { surname: pieces[0], given_name: '' };
        return {
          surname: pieces[pieces.length - 1],
          given_name: pieces.slice(0, -1).join(' '),
        };
      });
    }
    return trimmed;
  };

  // Check if a given conflict is answered
  const isConflictResolved = React.useCallback(
    (conf: ReviewConflict): boolean => {
      const item = resolutions[conf.field];
      if (!item) return false;
      if (item.choice === 'custom') {
        return item.customValue.trim().length > 0;
      }
      return item.choice === 'crossref' || item.choice === 'openalex';
    },
    [resolutions]
  );

  const resolvedCount = useMemo(() => {
    return conflicts.filter((c) => isConflictResolved(c)).length;
  }, [conflicts, isConflictResolved]);

  // Handle selecting an option in the wizard
  const handleSelectChoice = (conf: ReviewConflict, choice: ConflictChoice) => {
    setValidationWarning(null);
    const existing = resolutions[conf.field] || { choice, customValue: '' };

    let defaultCustom = existing.customValue;
    if (!defaultCustom) {
      if (choice === 'crossref') {
        defaultCustom = formatDisplayValue(getCrossrefVal(conf));
      } else if (choice === 'openalex') {
        defaultCustom = formatDisplayValue(getOpenalexVal(conf));
      } else if (choice === 'custom') {
        defaultCustom = formatDisplayValue(getCrossrefVal(conf) || getOpenalexVal(conf));
      }
    }

    setResolutions({
      ...resolutions,
      [conf.field]: {
        choice,
        customValue: defaultCustom,
      },
    });
  };

  const handleCustomTextChange = (conf: ReviewConflict, text: string) => {
    setValidationWarning(null);
    setResolutions({
      ...resolutions,
      [conf.field]: {
        choice: 'custom',
        customValue: text,
      },
    });
  };

  // Author manipulations for full form view
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

  // Submit from Conflict Wizard
  const handleSaveFromWizard = async () => {
    setValidationWarning(null);
    setGeneralError(null);

    // Validate that every conflict has an answer
    const unresolvedIdx = conflicts.findIndex((c) => !isConflictResolved(c));
    if (unresolvedIdx !== -1) {
      const fieldName = conflicts[unresolvedIdx].field;
      const warnMsg = `Please resolve all conflicting fields before saving. (${fieldName} is still pending).`;
      setValidationWarning(warnMsg);
      dispatch(
        addToast({
          type: 'info',
          message: warnMsg,
        })
      );
      setCurrentConflictIdx(unresolvedIdx);
      return;
    }

    // Build edits object from user resolutions
    const edits: Record<string, unknown> = {};

    conflicts.forEach((conf) => {
      const decision = resolutions[conf.field];
      if (!decision) return;

      if (decision.choice === 'crossref') {
        edits[conf.field] = getCrossrefVal(conf);
      } else if (decision.choice === 'openalex') {
        edits[conf.field] = getOpenalexVal(conf);
      } else if (decision.choice === 'custom') {
        edits[conf.field] = parseCustomValue(conf.field, decision.customValue);
      }
    });

    setIsSubmitting(true);
    try {
      if (Object.keys(edits).length > 0) {
        await resume({ action: 'edit', edits });
      } else {
        await resume({ action: 'accept' });
      }
      dispatch(
        addToast({
          type: 'success',
          message: 'All conflicts resolved. Generating LaTeX citation document...',
        })
      );
      handleClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          await refetch();
          dispatch(addToast({ type: 'info', message: "This file's status changed." }));
          handleClose();
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

  // Submit from Full Form view
  const handleSaveFromFullForm = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError(null);
    setValidationWarning(null);

    const edits: Record<string, unknown> = {};
    if (title.trim()) edits.title = title.trim();
    if (year.trim()) edits.year = parseInt(year.trim(), 10) || year.trim();
    if (journal.trim()) edits.journal = journal.trim();
    if (journalAbbr.trim()) edits.journal_abbreviation = journalAbbr.trim();
    if (doiUrl.trim()) edits.doi_url = doiUrl.trim();
    if (volume.trim()) edits.volume = volume.trim();
    if (issue.trim()) edits.issue = issue.trim();
    if (firstPage.trim()) edits.first_page = firstPage.trim();
    if (articleNumber.trim()) edits.article_number = articleNumber.trim();

    const cleanAuthors = authors
      .map((a) => [a.given_name, a.middle_name, a.surname].filter(Boolean).join(' ').trim())
      .filter(Boolean);

    if (cleanAuthors.length > 0) {
      edits.authors = authors.map((a) => ({
        given_name: a.given_name || '',
        middle_name: a.middle_name || '',
        surname: a.surname || '',
      }));
    }

    setIsSubmitting(true);
    try {
      if (Object.keys(edits).length > 0) {
        await resume({ action: 'edit', edits });
      } else {
        await resume({ action: 'accept' });
      }
      dispatch(
        addToast({
          type: 'success',
          message: 'Saved metadata edits. Generating LaTeX citation document...',
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

  const currentConflict = conflicts[currentConflictIdx] as ReviewConflict | undefined;
  const currentResolution = currentConflict ? resolutions[currentConflict.field] : undefined;

  return (
    <Modal
      isOpen={true}
      onClose={handleClose}
      title={viewMode === 'wizard' ? 'Review Citation Discrepancies' : 'Review Citation Metadata'}
      description={
        viewMode === 'wizard'
          ? 'Resolve differences detected between Crossref and OpenAlex.'
          : 'Inspect cross-referenced metadata before generating your LaTeX citation document.'
      }
      maxWidth="75p"
    >
      <div className="space-y-5 font-sans">
        {/* Error Banners */}
        {generalError && (
          <div
            className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 leading-relaxed font-sans flex items-start gap-2 animate-in fade-in duration-150"
            role="alert"
          >
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span>{generalError}</span>
          </div>
        )}

        {validationWarning && (
          <div
            className="p-3.5 rounded-xl bg-amber-50 border border-amber-300 text-xs text-amber-900 leading-relaxed font-sans flex items-start gap-2 animate-in fade-in duration-150 shadow-xs"
            role="alert"
          >
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold block mb-0.5">Selection Required</span>
              <span>{validationWarning}</span>
            </div>
          </div>
        )}

        {/* Pipeline Notices/Warnings */}
        {warnings.length > 0 && (
          <div className="p-3 rounded-xl bg-amber-50/80 border border-amber-200 space-y-1 text-xs text-amber-900">
            <div className="flex items-center gap-1.5 font-semibold font-mono uppercase tracking-wider text-[10px]">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              <span>Pipeline Notice</span>
            </div>
            {warnings.map((w, idx) => (
              <p key={idx} className="font-sans pl-5 leading-relaxed text-[11px] text-amber-800">
                {w}
              </p>
            ))}
          </div>
        )}

        {/* View Mode Toggle Button */}
        {conflicts.length > 0 && (
          <div className="flex items-center justify-between pb-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-charcoal/50">
              {viewMode === 'wizard' ? 'Conflict Resolution Mode' : 'Full Metadata Form Mode'}
            </span>
            <button
              type="button"
              onClick={() => {
                setValidationWarning(null);
                setViewMode(viewMode === 'wizard' ? 'full_form' : 'wizard');
              }}
              className="inline-flex items-center gap-1.5 text-xs text-indigo-brand hover:text-indigo-hover font-medium underline underline-offset-4 cursor-pointer"
            >
              <ListFilter className="w-3.5 h-3.5" />
              <span>
                {viewMode === 'wizard' ? 'Switch to Full Form' : 'Switch to Conflict Wizard'}
              </span>
            </button>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 1: STEP-BY-STEP CONFLICT RESOLUTION WIZARD                           */}
        {/* ========================================================================= */}
        {viewMode === 'wizard' && currentConflict && (
          <div className="space-y-4">
            {/* Wizard Header & Progress Bar */}
            <div className="rounded-xl border border-border-light bg-cream-50/60 p-3.5 space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono uppercase tracking-wider text-[11px] font-semibold text-charcoal-700">
                  Step {currentConflictIdx + 1} of {conflicts.length}
                </span>
                <div className="flex items-center gap-3 font-mono text-[11px]">
                  <span className="text-emerald-700 font-medium flex items-center gap-1">
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
                    Resolved: {resolvedCount}
                  </span>
                  <span className="text-charcoal/50 font-medium flex items-center gap-1">
                    <span className="inline-block w-2 h-2 rounded-full bg-cream-300" />
                    Pending: {conflicts.length - resolvedCount}
                  </span>
                </div>
              </div>

              {/* Progress: [====== Resolved ======] [------ Pending ------] */}
              <div className="w-full h-2 rounded-full bg-cream-200 overflow-hidden border border-border-light flex">
                <div
                  className="h-full bg-emerald-600 transition-all duration-300"
                  style={{ width: `${(resolvedCount / conflicts.length) * 100}%` }}
                />
                <div
                  className="h-full bg-cream-300/80 transition-all duration-300"
                  style={{ width: `${((conflicts.length - resolvedCount) / conflicts.length) * 100}%` }}
                />
              </div>

              {/* Progress step indicators */}
              <div className="flex items-center gap-1.5 overflow-x-auto pt-1">
                {conflicts.map((c, i) => {
                  const isDone = isConflictResolved(c);
                  const isCurrent = i === currentConflictIdx;
                  return (
                    <button
                      key={c.field}
                      type="button"
                      onClick={() => {
                        setValidationWarning(null);
                        setCurrentConflictIdx(i);
                      }}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-mono uppercase tracking-wider transition-all flex items-center gap-1 cursor-pointer border ${
                        isCurrent
                          ? 'bg-indigo-brand text-white border-indigo-brand shadow-xs font-semibold'
                          : isDone
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
                          : 'bg-white text-charcoal/60 border-border-light hover:bg-cream-100'
                      }`}
                    >
                      {isDone && <Check className="w-3 h-3 text-emerald-600" />}
                      <span>{c.field}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Conflicting Field Banner */}
            <div className="p-3.5 rounded-xl bg-indigo-50/60 border border-indigo-200/80">
              <div className="flex items-center gap-2 text-indigo-950 font-mono text-xs uppercase tracking-wider font-semibold">
                <HelpCircle className="w-4 h-4 text-indigo-brand shrink-0" />
                <span>Field in Conflict: {currentConflict.field.replace('_', ' ')}</span>
              </div>
              <p className="mt-1 pl-6 text-xs text-charcoal/70 leading-relaxed">
                {currentConflict.reason ||
                  'Discrepancy detected between bibliographic metadata providers.'}
              </p>
            </div>

            {/* Three Selection Options */}
            <div className="space-y-3">
              {/* Option A: Crossref */}
              <div
                role="button"
                tabIndex={0}
                onClick={() => handleSelectChoice(currentConflict, 'crossref')}
                onKeyDown={(e) => {
                  if (e.key === ' ' || e.key === 'Enter') {
                    handleSelectChoice(currentConflict, 'crossref');
                  }
                }}
                className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
                  currentResolution?.choice === 'crossref'
                    ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20 shadow-xs'
                    : 'border-border-light bg-white hover:border-indigo-200 hover:bg-cream-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-4 h-4 rounded-full border mt-0.5 flex items-center justify-center shrink-0 transition-all ${
                      currentResolution?.choice === 'crossref'
                        ? 'border-indigo-brand bg-indigo-brand text-white'
                        : 'border-charcoal/30 bg-white'
                    }`}
                  >
                    {currentResolution?.choice === 'crossref' && (
                      <div className="w-1.5 h-1.5 rounded-full bg-white" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-xs text-charcoal-900">
                        Option A &mdash; Crossref
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200 font-medium">
                        Crossref Source
                      </span>
                    </div>
                    <div className="text-xs text-charcoal-800 leading-relaxed font-mono bg-white/70 p-2 rounded-lg border border-indigo-100/50 break-words">
                      {formatDisplayValue(getCrossrefVal(currentConflict))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Option B: OpenAlex */}
              <div
                role="button"
                tabIndex={0}
                onClick={() => handleSelectChoice(currentConflict, 'openalex')}
                onKeyDown={(e) => {
                  if (e.key === ' ' || e.key === 'Enter') {
                    handleSelectChoice(currentConflict, 'openalex');
                  }
                }}
                className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
                  currentResolution?.choice === 'openalex'
                    ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20 shadow-xs'
                    : 'border-border-light bg-white hover:border-indigo-200 hover:bg-cream-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-4 h-4 rounded-full border mt-0.5 flex items-center justify-center shrink-0 transition-all ${
                      currentResolution?.choice === 'openalex'
                        ? 'border-indigo-brand bg-indigo-brand text-white'
                        : 'border-charcoal/30 bg-white'
                    }`}
                  >
                    {currentResolution?.choice === 'openalex' && (
                      <div className="w-1.5 h-1.5 rounded-full bg-white" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-xs text-charcoal-900">
                        Option B &mdash; OpenAlex
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                        OpenAlex Source
                      </span>
                    </div>
                    <div className="text-xs text-charcoal-800 leading-relaxed font-mono bg-white/70 p-2 rounded-lg border border-indigo-100/50 break-words">
                      {formatDisplayValue(getOpenalexVal(currentConflict))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Option C: Custom / Enter My Own */}
              <div
                className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                  currentResolution?.choice === 'custom'
                    ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20 shadow-xs'
                    : 'border-border-light bg-white hover:border-indigo-200'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => handleSelectChoice(currentConflict, 'custom')}
                    className={`w-4 h-4 rounded-full border mt-0.5 flex items-center justify-center shrink-0 cursor-pointer transition-all ${
                      currentResolution?.choice === 'custom'
                        ? 'border-indigo-brand bg-indigo-brand text-white'
                        : 'border-charcoal/30 bg-white'
                    }`}
                  >
                    {currentResolution?.choice === 'custom' && (
                      <div className="w-1.5 h-1.5 rounded-full bg-white" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0 space-y-2">
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => handleSelectChoice(currentConflict, 'custom')}
                      className="flex items-center justify-between cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-charcoal-900 flex items-center gap-1.5">
                          <Edit3 className="w-3.5 h-3.5 text-indigo-brand" />
                          <span>Option C &mdash; Custom / Enter My Own</span>
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-purple-50 text-purple-700 border border-purple-200 font-medium">
                          Custom
                        </span>
                      </div>

                      {/* Quick copy buttons */}
                      {currentResolution?.choice === 'custom' && (
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCustomTextChange(
                                currentConflict,
                                formatDisplayValue(getCrossrefVal(currentConflict))
                              );
                            }}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-charcoal/70 bg-white border border-border-light hover:bg-cream-200"
                            title="Copy Crossref text into custom field"
                          >
                            <Copy className="w-3 h-3" />
                            <span>Copy Crossref</span>
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCustomTextChange(
                                currentConflict,
                                formatDisplayValue(getOpenalexVal(currentConflict))
                              );
                            }}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-charcoal/70 bg-white border border-border-light hover:bg-cream-200"
                            title="Copy OpenAlex text into custom field"
                          >
                            <Copy className="w-3 h-3" />
                            <span>Copy OpenAlex</span>
                          </button>
                        </div>
                      )}
                    </div>

                    {currentResolution?.choice === 'custom' && (
                      <div className="pt-1">
                        {currentConflict.field === 'authors' ? (
                          <textarea
                            rows={3}
                            placeholder="e.g. Masheyeva R; Tikhonov A; Smith J"
                            value={currentResolution.customValue}
                            onChange={(e) =>
                              handleCustomTextChange(currentConflict, e.target.value)
                            }
                            className="w-full text-xs font-mono p-2.5 rounded-lg border border-border-light bg-white focus:outline-none focus:ring-2 focus:ring-indigo-brand text-charcoal-900"
                          />
                        ) : (
                          <input
                            type="text"
                            placeholder={`Enter custom ${currentConflict.field}...`}
                            value={currentResolution.customValue}
                            onChange={(e) =>
                              handleCustomTextChange(currentConflict, e.target.value)
                            }
                            className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-border-light bg-white focus:outline-none focus:ring-2 focus:ring-indigo-brand text-charcoal-900"
                          />
                        )}
                        <span className="text-[10px] font-mono text-charcoal/50 mt-1 block">
                          Enter your exact preferred value for this publication field.
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Navigation & Submission Footer */}
            <div className="sticky bottom-0 bg-cream/95 backdrop-blur-xs pt-3.5 pb-1 border-t border-border-light -mx-6 px-6 mt-4 z-10 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <Button
                type="button"
                variant="ghost"
                onClick={handleSkip}
                disabled={isSubmitting}
                className="text-xs text-charcoal/60 hover:text-charcoal font-mono"
              >
                Skip this file
              </Button>

              <div className="flex items-center gap-2 justify-end">
                {/* Previous Button */}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setValidationWarning(null);
                    setCurrentConflictIdx((prev) => Math.max(0, prev - 1));
                  }}
                  disabled={currentConflictIdx === 0 || isSubmitting}
                  className="gap-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span>Previous</span>
                </Button>

                {/* Next Field Button */}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setValidationWarning(null);
                    setCurrentConflictIdx((prev) =>
                      Math.min(conflicts.length - 1, prev + 1)
                    );
                  }}
                  disabled={currentConflictIdx >= conflicts.length - 1 || isSubmitting}
                  className="gap-1 text-indigo-brand border-indigo-200 hover:bg-indigo-50/60 disabled:opacity-40"
                >
                  <span>Next Field</span>
                  <ChevronRight className="w-4 h-4" />
                </Button>

                {/* Save & Generate .tex Button */}
                <Button
                  type="button"
                  variant="primary"
                  onClick={handleSaveFromWizard}
                  isLoading={isSubmitting}
                  className="gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5 text-indigo-200" />
                  <span>Save & Generate .tex</span>
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 2: FULL METADATA EDIT FORM (Fallback & Advanced Inspection)          */}
        {/* ========================================================================= */}
        {viewMode === 'full_form' && (
          <form onSubmit={handleSaveFromFullForm} className="space-y-4">
            <div className="max-h-[60vh] overflow-y-auto pr-1 space-y-4">
              {/* Title */}
              <Input
                label="Title"
                placeholder="Article or paper title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                error={fieldErrors.title}
                required
                disabled={isSubmitting}
              />

              {/* Authors Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono uppercase tracking-wider text-charcoal/80 font-medium">
                    Authors ({authors.length})
                  </label>
                  <button
                    type="button"
                    onClick={handleAddAuthor}
                    disabled={isSubmitting}
                    className="inline-flex items-center gap-1 text-xs text-indigo-brand hover:text-indigo-hover font-medium cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Author</span>
                  </button>
                </div>

                <div className="space-y-2">
                  {authors.map((auth, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-charcoal/40 w-4 text-center">
                        {idx + 1}
                      </span>
                      <input
                        type="text"
                        placeholder="Given / First Name"
                        value={auth.given_name || ''}
                        onChange={(e) => handleAuthorChange(idx, 'given_name', e.target.value)}
                        disabled={isSubmitting}
                        className="flex-1 text-xs font-sans px-3 py-1.5 rounded-lg border border-border-light bg-white focus:outline-none focus:ring-2 focus:ring-indigo-brand text-charcoal-900"
                      />
                      <input
                        type="text"
                        placeholder="Surname / Last Name"
                        value={auth.surname || ''}
                        onChange={(e) => handleAuthorChange(idx, 'surname', e.target.value)}
                        disabled={isSubmitting}
                        className="flex-1 text-xs font-sans px-3 py-1.5 rounded-lg border border-border-light bg-white focus:outline-none focus:ring-2 focus:ring-indigo-brand text-charcoal-900"
                      />
                      <div className="flex items-center gap-0.5">
                        <button
                          type="button"
                          onClick={() => handleMoveAuthor(idx, 'up')}
                          disabled={idx === 0 || isSubmitting}
                          className="p-1 text-charcoal/40 hover:text-charcoal disabled:opacity-30 cursor-pointer"
                          title="Move Up"
                        >
                          <ArrowUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMoveAuthor(idx, 'down')}
                          disabled={idx === authors.length - 1 || isSubmitting}
                          className="p-1 text-charcoal/40 hover:text-charcoal disabled:opacity-30 cursor-pointer"
                          title="Move Down"
                        >
                          <ArrowDown className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRemoveAuthor(idx)}
                          disabled={authors.length <= 1 || isSubmitting}
                          className="p-1 text-red-500/60 hover:text-red-600 disabled:opacity-30 cursor-pointer"
                          title="Delete Author"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Journal / Venue & Abbreviation */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Journal / Venue"
                  placeholder="e.g. Plasma Sources Sci. Technol."
                  value={journal}
                  onChange={(e) => setJournal(e.target.value)}
                  error={fieldErrors.journal}
                  disabled={isSubmitting}
                />
                <Input
                  label="Journal Abbreviation"
                  placeholder="e.g. PSST"
                  value={journalAbbr}
                  onChange={(e) => setJournalAbbr(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>

              {/* Year & DOI */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Publication Year"
                  placeholder="e.g. 2025"
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  error={fieldErrors.year}
                  disabled={isSubmitting}
                />
                <Input
                  label="DOI URL"
                  placeholder="https://doi.org/10.xxxx/..."
                  value={doiUrl}
                  onChange={(e) => setDoiUrl(e.target.value)}
                  error={fieldErrors.doi_url}
                  disabled={isSubmitting}
                />
              </div>

              {/* Volume, Issue, Pages, Article No. */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Input
                  label="Volume"
                  placeholder="e.g. 34"
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
                  placeholder="e.g. 1"
                  value={firstPage}
                  onChange={(e) => setFirstPage(e.target.value)}
                  disabled={isSubmitting}
                />
                <Input
                  label="Article No."
                  placeholder="e.g. 045017"
                  value={articleNumber}
                  onChange={(e) => setArticleNumber(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>

            {/* Footer Actions */}
            <div className="sticky bottom-0 bg-cream/95 backdrop-blur-xs pt-3.5 pb-1 border-t border-border-light -mx-6 px-6 mt-4 z-10 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <Button
                type="button"
                variant="ghost"
                onClick={handleSkip}
                disabled={isSubmitting}
                className="text-xs text-charcoal/60 hover:text-charcoal font-mono"
              >
                Skip this file
              </Button>

              <div className="flex items-center gap-2 justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={async () => {
                    setIsSubmitting(true);
                    try {
                      await resume({ action: 'accept' });
                      dispatch(
                        addToast({
                          type: 'success',
                          message: 'Accepted citation metadata. Generating LaTeX document...',
                        })
                      );
                      handleClose();
                    } catch (err: unknown) {
                      setGeneralError(getErrorMessage(err));
                    } finally {
                      setIsSubmitting(false);
                    }
                  }}
                  disabled={isSubmitting}
                  className="gap-1.5"
                >
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Accept As Is</span>
                </Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting} className="gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-200" />
                  <span>Save & Generate .tex</span>
                </Button>
              </div>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
};

export const ReviewFormDialog: React.FC = () => {
  const activeJobId = useAppSelector((state) => state.jobs.activeReviewJobId);
  if (!activeJobId) return null;

  return <ReviewFormInner key={activeJobId} jobId={activeJobId} />;
};
