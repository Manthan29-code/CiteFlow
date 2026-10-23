import React, { useRef, useState, useMemo } from 'react';
import { FolderPlus, Upload, Search, LayoutList, LayoutGrid, X, Sparkles, Loader2 } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openNewFolderModal, addToast } from '@/store/slices/uiSlice';
import { setSearchQuery, setViewMode } from '@/store/slices/explorerSlice';
import { openJobDrawer, setJobs } from '@/store/slices/jobsSlice';
import { addUploads } from '@/store/slices/uploadSlice';
import { Button } from '@/components/common/Button';
import { UploadQueueItem } from '@/types/api';
import { env } from '@/lib/env';
import { formatBytes } from '@/lib/format';
import { createFolderJobs } from '@/api/jobs';
import { getErrorMessage } from '@/api/errors';

export const Toolbar: React.FC = () => {
  const dispatch = useAppDispatch();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { searchQuery, viewMode, folderData } = useAppSelector((state) => state.explorer);
  const jobsById = useAppSelector((state) => state.jobs.jobsById);
  const currentFolder = folderData?.folder;

  const [isBatchGenerating, setIsBatchGenerating] = useState(false);

  const pdfFiles = useMemo(() => {
    return (folderData?.files || []).filter((f) => f.ext.toLowerCase() === 'pdf');
  }, [folderData?.files]);

  // Find active or recent job for easy re-opening
  const activeJob = React.useMemo(
    () =>
      Object.values(jobsById).find((j) =>
        ['queued', 'running', 'needs_title_confirmation', 'needs_review'].includes(j.status)
      ) ||
      Object.values(jobsById).sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0],
    [jobsById]
  );

  const totalItems = (folderData?.folders.length || 0) + (folderData?.files.length || 0);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    if (!currentFolder?.id) {
      dispatch(
        addToast({
          type: 'error',
          message: 'Folder not ready for uploads.',
        })
      );
      return;
    }

    const files = Array.from(e.target.files);
    const newItems: UploadQueueItem[] = [];
    const rejectedReasons: string[] = [];

    files.forEach((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';

      if (!env.VITE_ALLOWED_EXTENSIONS.includes(ext)) {
        rejectedReasons.push(`"${file.name}": Only PDF files are supported.`);
        return;
      }

      const maxBytes = env.VITE_MAX_UPLOAD_MB * 1024 * 1024;
      if (file.size > maxBytes) {
        rejectedReasons.push(
          `"${file.name}" (${formatBytes(file.size)}) exceeds ${env.VITE_MAX_UPLOAD_MB} MB limit.`
        );
        return;
      }

      newItems.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        file,
        name: file.name,
        sizeBytes: file.size,
        folderId: currentFolder.id,
        folderName: currentFolder.name,
        progress: 0,
        status: 'queued',
      });
    });

    if (rejectedReasons.length > 0) {
      dispatch(
        addToast({
          type: 'error',
          message: rejectedReasons.join(' | '),
        })
      );
    }

    if (newItems.length > 0) {
      dispatch(addUploads(newItems));
    }

    // Reset input so same file can be picked again if desired
    e.target.value = '';
  };

  const handleGenerateFolderCitations = async () => {
    if (!currentFolder?.id || isBatchGenerating) return;
    setIsBatchGenerating(true);
    try {
      const jobs = await createFolderJobs(currentFolder.id);
      dispatch(setJobs(jobs));
      const newlyStarted = jobs.filter((j) => ['queued', 'running'].includes(j.status)).length;
      dispatch(
        addToast({
          type: 'success',
          message:
            newlyStarted > 0
              ? `Started citation generation for ${newlyStarted} files in "${currentFolder.name}".`
              : `All citations in "${currentFolder.name}" are already generated or processing.`,
        })
      );
      // NOTE: We deliberately do NOT call openJobDrawer() so the side drawer remains closed during batch!
    } catch (err: unknown) {
      dispatch(
        addToast({
          type: 'error',
          message: `Failed to start folder citations: ${getErrorMessage(err)}`,
        })
      );
    } finally {
      setIsBatchGenerating(false);
    }
  };

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-border-light">
      {/* Left Action Buttons */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          onClick={() => dispatch(openNewFolderModal())}
          className="gap-1.5"
        >
          <FolderPlus className="w-4 h-4" />
          <span>New Folder</span>
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={handleUploadClick}
          className="gap-1.5"
        >
          <Upload className="w-4 h-4 text-indigo-brand" />
          <span>Upload PDF</span>
        </Button>

        {pdfFiles.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerateFolderCitations}
            disabled={isBatchGenerating}
            className="gap-1.5 text-indigo-brand border-indigo-200 bg-indigo-50/60 hover:bg-indigo-100/70 shadow-xs"
            title={`Generate .tex citation for all ${pdfFiles.length} PDF files in "${currentFolder?.name || 'this folder'}"`}
          >
            {isBatchGenerating ? (
              <Loader2 className="w-4 h-4 text-indigo-brand animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4 text-indigo-brand" />
            )}
            <span>
              {isBatchGenerating ? 'Starting...' : `Generate Folder .tex (${pdfFiles.length})`}
            </span>
          </Button>
        )}

        {activeJob && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => dispatch(openJobDrawer(activeJob.id))}
            className="gap-1.5 text-charcoal/60 hover:text-indigo-brand"
            title="Open Citation Pipeline details"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="text-xs">Pipeline</span>
          </Button>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept={env.VITE_ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(',')}
          multiple
          onChange={handleFileInputChange}
          className="hidden"
          aria-label="Upload files"
        />
      </div>

      {/* Right Controls: Search, View Switcher, Total count */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[140px] sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-charcoal/40" />
          <input
            type="text"
            placeholder="Search items..."
            value={searchQuery}
            onChange={(e) => dispatch(setSearchQuery(e.target.value))}
            className="w-full pl-9 pr-8 py-1.5 text-xs bg-white border border-border-light rounded-xl text-charcoal-900 placeholder:text-charcoal/40 focus:outline-none focus:ring-2 focus:ring-indigo-brand shadow-xs"
          />
          {searchQuery && (
            <button
              onClick={() => dispatch(setSearchQuery(''))}
              aria-label="Clear search"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-charcoal/40 hover:text-charcoal"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center p-0.5 rounded-xl border border-border-light bg-cream-200">
          <button
            onClick={() => dispatch(setViewMode('list'))}
            aria-label="List View"
            className={`p-1.5 rounded-lg transition-colors ${
              viewMode === 'list'
                ? 'bg-white text-indigo-brand shadow-xs'
                : 'text-charcoal/50 hover:text-charcoal'
            }`}
          >
            <LayoutList className="w-4 h-4" />
          </button>
          <button
            onClick={() => dispatch(setViewMode('grid'))}
            aria-label="Grid View"
            className={`p-1.5 rounded-lg transition-colors ${
              viewMode === 'grid'
                ? 'bg-white text-indigo-brand shadow-xs'
                : 'text-charcoal/50 hover:text-charcoal'
            }`}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
        </div>

        {/* Items Count Badge */}
        <span className="hidden lg:inline text-xs font-mono text-charcoal/50 uppercase tracking-wider">
          {totalItems} {totalItems === 1 ? 'item' : 'items'}
        </span>
      </div>
    </div>
  );
};
