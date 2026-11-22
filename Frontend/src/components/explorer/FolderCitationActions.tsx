import React, { useState, useMemo, useEffect } from 'react';
import { Sparkles, Loader2, Download } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openStyleManagerModal, addToast } from '@/store/slices/uiSlice';
import { setJobs, openGroupedTexModal } from '@/store/slices/jobsSlice';
import { Button } from '@/components/common/Button';
import { createFolderJobs } from '@/api/jobs';
import { getErrorMessage } from '@/api/errors';
import { cn } from '@/lib/utils';

export const FolderCitationActions: React.FC = () => {
  const dispatch = useAppDispatch();
  const { folderData } = useAppSelector((state) => state.explorer);
  const jobsByFileId = useAppSelector((state) => state.jobs.jobsByFileId);
  const { styles, selectedStyleId } = useAppSelector((state) => state.styles);
  const currentFolder = folderData?.folder;

  const [isBatchGenerating, setIsBatchGenerating] = useState(false);
  const [hasClickedGenerate, setHasClickedGenerate] = useState(false);

  useEffect(() => {
    setHasClickedGenerate(false);
  }, [currentFolder?.id]);

  const pdfFiles = useMemo(() => {
    return (folderData?.files || []).filter((f) => f.ext.toLowerCase() === 'pdf');
  }, [folderData?.files]);

  const succeededCount = useMemo(() => {
    return pdfFiles.filter((f) => jobsByFileId[f.id]?.status === 'succeeded').length;
  }, [pdfFiles, jobsByFileId]);

  const isDownloadClickable = hasClickedGenerate || succeededCount > 0;

  if (!currentFolder || pdfFiles.length === 0) {
    return null;
  }

  const handleGenerateFolderCitations = async () => {
    if (!currentFolder?.id || isBatchGenerating) return;

    if (styles.length === 0) {
      dispatch(
        addToast({
          type: 'error',
          message: "You can't generate citations when you don't have any citation style. Please add a style first.",
        })
      );
      dispatch(openStyleManagerModal());
      return;
    }

    setHasClickedGenerate(true);
    setIsBatchGenerating(true);
    try {
      const jobs = await createFolderJobs(currentFolder.id, 'standalone', selectedStyleId);
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
    <div className="flex items-center gap-2 shrink-0">
      <Button
        variant="outline"
        size="sm"
        onClick={handleGenerateFolderCitations}
        disabled={isBatchGenerating}
        className="gap-1.5 text-indigo-brand border-indigo-200 bg-indigo-50/60 hover:bg-indigo-100/70 shadow-xs"
        title={`Generate .tex citation for all ${pdfFiles.length} PDF files in "${currentFolder.name}"`}
      >
        {isBatchGenerating ? (
          <Loader2 className="w-4 h-4 text-indigo-brand animate-spin" />
        ) : (
          <Sparkles className="w-4 h-4 text-indigo-brand" />
        )}
        <span>
          {isBatchGenerating ? 'Starting...' : `Generate for All (${pdfFiles.length})`}
        </span>
      </Button>

      <Button
        variant="secondary"
        size="sm"
        onClick={() => dispatch(openGroupedTexModal(currentFolder.id))}
        disabled={!isDownloadClickable}
        className={cn(
          'border border-indigo-200 bg-white shadow-xs px-2.5 py-1.5',
          isDownloadClickable
            ? 'text-indigo-brand hover:bg-indigo-50/80 cursor-pointer'
            : 'text-indigo-brand/40 opacity-40 cursor-not-allowed'
        )}
        title={
          isDownloadClickable
            ? `Download grouped .tex citations for "${currentFolder.name}"`
            : 'Click "Generate for All" first to download citations'
        }
        aria-label="Download grouped citations"
      >
        <Download className="w-4 h-4 text-indigo-brand" />
      </Button>
    </div>
  );
};
