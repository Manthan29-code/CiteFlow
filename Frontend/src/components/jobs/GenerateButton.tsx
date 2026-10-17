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
      const job = await createJob(fileId, texMode);
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
        aria-label={`Generate .tex citation for ${fileName}`}
        className="inline-flex items-center gap-1.5 px-3 h-full rounded-l-xl bg-indigo-brand text-white text-xs font-sans font-medium hover:bg-indigo-hover active:bg-indigo-900 disabled:opacity-50 disabled:pointer-events-none transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand"
      >
        <Sparkles className="w-3.5 h-3.5 text-indigo-200 shrink-0" />
        <span className="whitespace-nowrap">{isStarting ? 'Starting...' : 'Generate .tex'}</span>
      </button>

      {/* Mode Selector Dropdown Arrow */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setDropdownOpen(!dropdownOpen);
        }}
        disabled={disabled || isStarting}
        aria-label="Choose TeX output mode"
        className="inline-flex items-center justify-center px-2.5 h-full rounded-r-xl border-l border-indigo-700/60 bg-indigo-brand text-indigo-200 hover:text-white hover:bg-indigo-hover active:bg-indigo-900 disabled:opacity-50 disabled:pointer-events-none transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand"
      >
        <ChevronDown className="w-3.5 h-3.5" />
      </button>

      {/* Dropdown Menu */}
      {dropdownOpen && (
        <div
          className={cn(
            'absolute right-0 z-50 w-52 rounded-xl bg-white border border-border-light shadow-xl p-1.5 text-xs font-sans text-charcoal-900 animate-in fade-in zoom-in-95 duration-100',
            openUpward ? 'bottom-full mb-1.5' : 'top-full mt-1.5'
          )}
        >
          <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-charcoal/50">
            Output Format
          </div>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setTexMode('standalone');
              setDropdownOpen(false);
            }}
            className="w-full flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-cream-200 transition-colors text-left"
          >
            <div>
              <div className="font-medium text-charcoal-900">Full Document</div>
              <div className="text-[10px] text-charcoal/50">Standalone LaTeX file</div>
            </div>
            {texMode === 'standalone' && <Check className="w-3.5 h-3.5 text-indigo-brand" />}
          </button>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setTexMode('fragment');
              setDropdownOpen(false);
            }}
            className="w-full flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-cream-200 transition-colors text-left"
          >
            <div>
              <div className="font-medium text-charcoal-900">Bibliography Block</div>
              <div className="text-[10px] text-charcoal/50">\begin&#123;thebibliography&#125;</div>
            </div>
            {texMode === 'fragment' && <Check className="w-3.5 h-3.5 text-indigo-brand" />}
          </button>
        </div>
      )}
    </div>
  );
};
