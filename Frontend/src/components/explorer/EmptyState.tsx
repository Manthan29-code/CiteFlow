import React from 'react';
import { FolderOpen, Upload, FolderPlus } from 'lucide-react';
import { useAppDispatch } from '@/store/hooks';
import { openNewFolderModal } from '@/store/slices/uiSlice';
import { Button } from '@/components/common/Button';

export interface EmptyStateProps {
  onUploadClick: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onUploadClick }) => {
  const dispatch = useAppDispatch();

  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center flex-1 rounded-2xl border border-border-light bg-white shadow-xs">
      <div className="w-16 h-16 rounded-2xl bg-cream-200 border border-border-light flex items-center justify-center text-charcoal/40 mb-4 shadow-sm">
        <FolderOpen className="w-8 h-8 text-indigo-brand/50" />
      </div>
      <h3 className="font-serif text-2xl font-bold text-charcoal-900 mb-1">
        This folder is empty
      </h3>
      <p className="text-xs sm:text-sm text-charcoal/60 font-sans max-w-sm mb-6">
        Begin by creating a subfolder or drag and drop PDF research papers directly here.
      </p>
      <div className="flex items-center gap-3">
        <Button
          variant="primary"
          size="sm"
          onClick={onUploadClick}
          className="gap-2"
        >
          <Upload className="w-4 h-4" />
          <span>Upload PDF</span>
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => dispatch(openNewFolderModal())}
          className="gap-2"
        >
          <FolderPlus className="w-4 h-4" />
          <span>New Folder</span>
        </Button>
      </div>
    </div>
  );
};
