import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, ChevronDown, Check } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setJob, setStartingJob, openJobDrawer } from '@/store/slices/jobsSlice';
import { addToast } from '@/store/slices/uiSlice';
import { createJob } from '@/api/jobs';
import { ApiError, getErrorMessage } from '@/api/errors';
import { TexMode } from '@/types/api';
import { cn } from '@/lib/utils';

export interface GenerateButtonProps {
  fileId: string;
  fileName: string;
  disabled?: boolean;
  className?: string;
}

export const GenerateButton: React.FC<GenerateButtonProps> = ({
  fileId,
  fileName,
  disabled = false,
  className,
}) => {
  const dispatch = useAppDispatch();
  const isStarting = useAppSelector((state) => state.jobs.isStartingJobByFileId[fileId] || false);
  const selectedStyleId = useAppSelector((state) => state.styles.selectedStyleId);

  const [texMode, setTexMode] = useState<TexMode>('standalone');
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [openUpward, setOpenUpward] = useState<boolean>(false);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    if (dropdownOpen) {
      if (dropdownRef.current) {
        const rect = dropdownRef.current.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        setOpenUpward(spaceBelow < 160);
      }
      document.addEventListener('mousedown', handleOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutside);
    };
  }, [dropdownOpen]);

  const handleStartJob = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isStarting || disabled) return;

    // Immediately disable button to prevent double clicks
    dispatch(setStartingJob({ fileId, isStarting: true }));

    try {
      const job = await createJob(fileId, texMode, selectedStyleId);
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

  return (
    <div
      className={cn('relative inline-flex items-stretch h-8 rounded-xl bg-indigo-brand shadow-xs', className)}
      ref={dropdownRef}
    >
      {/* Primary Action Button */}
      <button
        type="button"
        onClick={handleStartJob}
        disabled={disabled || isStarting}
        title="Generate .tex citation"
        aria-label="Generate citation"
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-semibold text-white rounded-l-xl transition-all',
          'hover:bg-indigo-hover active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand focus-visible:ring-offset-1'
        )}
      >
        <Sparkles className={cn('w-3.5 h-3.5', isStarting && 'animate-spin')} />
        <span className="hidden xs:inline">
          {isStarting ? 'Starting...' : 'Generate .tex'}
        </span>
      </button>

      {/* Split Dropdown Trigger */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setDropdownOpen(!dropdownOpen);
        }}
        disabled={disabled || isStarting}
        aria-label="Select LaTeX export mode"
        className={cn(
          'inline-flex items-center px-1.5 text-white/80 border-l border-white/20 rounded-r-xl transition-all',
          'hover:bg-indigo-hover hover:text-white disabled:opacity-50',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand focus-visible:ring-offset-1'
        )}
      >
        <ChevronDown className="w-3.5 h-3.5" />
      </button>

      {/* Floating Options Menu */}
      {dropdownOpen && (
        <div
          className={cn(
            'absolute right-0 z-50 w-56 rounded-xl bg-white border border-border-light shadow-xl py-1 text-xs font-sans text-charcoal-800 animate-in fade-in zoom-in-95 duration-100',
            openUpward ? 'bottom-full mb-1' : 'top-full mt-1'
          )}
        >
          <div className="px-3 py-1.5 text-[10px] font-mono text-charcoal/40 uppercase tracking-widest border-b border-border-light/60">
            Export Mode
          </div>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setTexMode('standalone');
              setDropdownOpen(false);
            }}
            className={cn(
              'w-full flex items-start gap-2 px-3 py-2 text-left hover:bg-cream-200 transition-colors',
              texMode === 'standalone' && 'bg-indigo-50/50 text-indigo-brand'
            )}
          >
            <div className="mt-0.5">
              {texMode === 'standalone' ? (
                <Check className="w-3.5 h-3.5 text-indigo-brand" />
              ) : (
                <div className="w-3.5 h-3.5" />
              )}
            </div>
            <div>
              <div className="font-semibold text-charcoal-900">Standalone .tex</div>
              <div className="text-[11px] text-charcoal/60 leading-tight">
                Complete document with preamble &amp; hyperref setup.
              </div>
            </div>
          </button>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setTexMode('fragment');
              setDropdownOpen(false);
            }}
            className={cn(
              'w-full flex items-start gap-2 px-3 py-2 text-left hover:bg-cream-200 transition-colors',
              texMode === 'fragment' && 'bg-indigo-50/50 text-indigo-brand'
            )}
          >
            <div className="mt-0.5">
              {texMode === 'fragment' ? (
                <Check className="w-3.5 h-3.5 text-indigo-brand" />
              ) : (
                <div className="w-3.5 h-3.5" />
              )}
            </div>
            <div>
              <div className="font-semibold text-charcoal-900">Bibliography Fragment</div>
              <div className="text-[11px] text-charcoal/60 leading-tight">
                Snippet for pasting into an existing document.
              </div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
};
