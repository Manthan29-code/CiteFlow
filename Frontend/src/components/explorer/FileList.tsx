import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { loadMoreFolderItems, fetchFolder } from '@/store/slices/explorerSlice';
import { setJob } from '@/store/slices/jobsSlice';
import { listJobs } from '@/api/jobs';
import { FileRow } from './FileRow';
import { EmptyState } from './EmptyState';
import { FolderNotFound } from './FolderNotFound';
import { Button } from '@/components/common/Button';
import { Spinner } from '@/components/common/Spinner';
import { AlertCircle, RotateCcw } from 'lucide-react';

export interface FileListProps {
  onUploadClick: () => void;
}

export const FileList: React.FC<FileListProps> = ({ onUploadClick }) => {
  const dispatch = useAppDispatch();
  const {
    folderData,
    isLoading,
    isLoadingMore,
    error,
    isNotFound,
    searchQuery,
    currentFolderId,
  } = useAppSelector((state) => state.explorer);

  // Sync existing jobs for status badges on page reload
  useEffect(() => {
    listJobs({ limit: 100 })
      .then((res) => {
        (res.items || []).forEach((job) => {
          dispatch(setJob(job));
        });
      })
      .catch(() => {});
  }, [dispatch, folderData?.folder?.id]);

  if (isNotFound) {
    return <FolderNotFound />;
  }

  if (isLoading && !folderData) {
    return (
      <div className="py-24 flex flex-col items-center justify-center">
        <Spinner size="lg" label="Loading Documents" />
      </div>
    );
  }

  if (error && !folderData) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-center px-4">
        <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center mb-3">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h3 className="font-serif text-xl font-bold text-charcoal-900 mb-1">
          Unable to Load Folder
        </h3>
        <p className="text-xs text-charcoal/60 mb-5 max-w-sm">{error}</p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => dispatch(fetchFolder(currentFolderId))}
          className="gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Try Again</span>
        </Button>
      </div>
    );
  }

  const allFolders = folderData?.folders || [];
  const allFiles = folderData?.files || [];

  // Filter based on search query
  const query = searchQuery.toLowerCase().trim();
  const filteredFolders = allFolders.filter((f) => f.name.toLowerCase().includes(query));
  const filteredFiles = allFiles.filter((f) => f.name.toLowerCase().includes(query));

  const totalFiltered = filteredFolders.length + filteredFiles.length;
  const isOriginalEmpty = allFolders.length === 0 && allFiles.length === 0;

  if (isOriginalEmpty) {
    return <EmptyState onUploadClick={onUploadClick} />;
  }

  if (totalFiltered === 0 && query) {
    return (
      <div className="py-20 text-center text-charcoal/60">
        <p className="font-serif text-lg text-charcoal-900 mb-1">No matches found</p>
        <p className="text-xs">No files or folders matched &ldquo;{searchQuery}&rdquo;.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full flex-1 min-h-0">
      <div className="overflow-x-auto flex-1 min-h-[340px] rounded-2xl border border-border-light bg-white shadow-xs">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border-light bg-cream-50 text-[11px] font-mono uppercase tracking-[0.2em] text-charcoal/60">
              <th className="py-3 px-4 font-semibold">Name</th>
              <th className="py-3 px-4 font-semibold hidden sm:table-cell">Size</th>
              <th className="py-3 px-4 font-semibold hidden md:table-cell">Created</th>
              <th className="py-3 px-4 font-semibold hidden sm:table-cell text-center">Citation</th>
              <th className="py-3 px-4 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-light">
            {/* Folders first */}
            {filteredFolders.map((folder) => (
              <FileRow key={folder.id} item={{ type: 'folder', data: folder }} />
            ))}

            {/* Files second */}
            {filteredFiles.map((file) => (
              <FileRow key={file.id} item={{ type: 'file', data: file }} />
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination: Load More */}
      {folderData?.next_cursor && (
        <div className="pt-6 pb-2 flex justify-center">
          <Button
            variant="outline"
            size="sm"
            onClick={() => dispatch(loadMoreFolderItems())}
            isLoading={isLoadingMore}
            className="text-xs font-mono"
          >
            Load More Items
          </Button>
        </div>
      )}
    </div>
  );
};
