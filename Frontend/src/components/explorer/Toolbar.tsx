import React, { useRef } from 'react';
import { FolderPlus, Upload, Search, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openNewFolderModal, addToast } from '@/store/slices/uiSlice';
import { setSearchQuery } from '@/store/slices/explorerSlice';
import { addUploads } from '@/store/slices/uploadSlice';
import { Button } from '@/components/common/Button';
import { StyleSelectorDropdown } from '@/components/styles/StyleSelectorDropdown';
import { UploadQueueItem } from '@/types/api';
import { env } from '@/lib/env';
import { formatBytes } from '@/lib/format';

export const Toolbar: React.FC = () => {
  const dispatch = useAppDispatch();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { searchQuery, folderData } = useAppSelector((state) => state.explorer);
  const currentFolder = folderData?.folder;

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

        {/* Style Selector Dropdown */}
        <StyleSelectorDropdown />

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

      {/* Right Controls: Search & Total count */}
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

        <span className="text-[11px] font-mono text-charcoal/40 uppercase whitespace-nowrap hidden sm:inline-block">
          {totalItems} {totalItems === 1 ? 'item' : 'items'}
        </span>
      </div>
    </div>
  );
};
