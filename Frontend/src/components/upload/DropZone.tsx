import React, { useState, useCallback, useRef } from 'react';
import { Upload } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { addUploads } from '@/store/slices/uploadSlice';
import { addToast } from '@/store/slices/uiSlice';
import { UploadQueueItem } from '@/types/api';
import { env } from '@/lib/env';
import { formatBytes } from '@/lib/format';

export interface DropZoneProps {
  children: React.ReactNode;
}

export const DropZone: React.FC<DropZoneProps> = ({ children }) => {
  const dispatch = useAppDispatch();
  const currentFolder = useAppSelector((state) => state.explorer.folderData?.folder);
  const [isDragOver, setIsDragOver] = useState(false);
  const dragCounter = useRef(0);

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      if (!currentFolder?.id) {
        dispatch(
          addToast({
            type: 'error',
            message: 'Cannot upload files: current folder not ready.',
          })
        );
        return;
      }

      const fileList = Array.from(files);
      const newItems: UploadQueueItem[] = [];
      const rejectedReasons: string[] = [];

      fileList.forEach((file) => {
        const ext = file.name.split('.').pop()?.toLowerCase() || '';

        // Pre-check 1: extension
        if (!env.VITE_ALLOWED_EXTENSIONS.includes(ext)) {
          rejectedReasons.push(
            `"${file.name}": Only ${env.VITE_ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(', ')} files are supported.`
          );
          return;
        }

        // Pre-check 2: size
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
    },
    [currentFolder, dispatch]
  );

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current += 1;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current -= 1;
    if (dragCounter.current === 0) {
      setIsDragOver(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    dragCounter.current = 0;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className="relative w-full h-full min-h-[400px]"
    >
      {children}

      {/* Drag Overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-40 bg-indigo-50/90 backdrop-blur-xs border-2 border-dashed border-indigo-brand rounded-2xl flex flex-col items-center justify-center p-6 pointer-events-none transition-all">
          <div className="w-16 h-16 rounded-full bg-indigo-brand/10 flex items-center justify-center text-indigo-brand mb-4 animate-bounce">
            <Upload className="w-8 h-8" />
          </div>
          <h3 className="font-serif text-2xl font-bold text-charcoal-900">
            Drop PDFs to Upload
          </h3>
          <p className="mt-2 text-xs font-mono text-charcoal/70 tracking-widest uppercase">
            Uploading into &ldquo;{currentFolder?.name || 'Current Folder'}&rdquo; &bull; Max {env.VITE_MAX_UPLOAD_MB} MB
          </p>
        </div>
      )}
    </div>
  );
};
