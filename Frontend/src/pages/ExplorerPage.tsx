import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchFolder } from '@/store/slices/explorerSlice';
import { fetchStyles } from '@/store/slices/stylesSlice';
import { Navbar } from '@/components/layout/Navbar';
import { Sidebar } from '@/components/layout/Sidebar';
import { Breadcrumbs } from '@/components/layout/Breadcrumbs';
import { Toolbar } from '@/components/explorer/Toolbar';
import { FileList } from '@/components/explorer/FileList';
import { NewFolderDialog } from '@/components/explorer/NewFolderDialog';
import { DeleteConfirmDialog } from '@/components/explorer/DeleteConfirmDialog';
import { TitleConfirmDialog } from '@/components/jobs/TitleConfirmDialog';
import { ReviewFormDialog } from '@/components/jobs/ReviewFormDialog';
import { TexPreviewDialog } from '@/components/jobs/TexPreviewDialog';
import { StyleManagerDialog } from '@/components/styles/StyleManagerDialog';
import { JobPanel } from '@/components/jobs/JobPanel';
import { ActiveJobDock } from '@/components/jobs/ActiveJobDock';
import { UploadDrawer } from '@/components/upload/UploadDrawer';
import { DropZone } from '@/components/upload/DropZone';
import { addUploads } from '@/store/slices/uploadSlice';
import { addToast } from '@/store/slices/uiSlice';
import { UploadQueueItem } from '@/types/api';
import { useActiveJobsSync } from '@/hooks/useActiveJobsSync';
import { env } from '@/lib/env';
import { formatBytes } from '@/lib/format';

const EMPTY_BREADCRUMBS: [] = [];

export const ExplorerPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const { folderId } = useParams<{ folderId?: string }>();
  const activeId = folderId || 'root';
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Reactively sync active jobs every 8s and on tab focus
  useActiveJobsSync();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const breadcrumbs = useAppSelector((state) => state.explorer.folderData?.breadcrumbs) || EMPTY_BREADCRUMBS;
  const currentFolder = useAppSelector((state) => state.explorer.folderData?.folder);

  // Synchronize route param with folder query & load styles
  useEffect(() => {
    dispatch(fetchFolder(activeId));
    dispatch(fetchStyles());
  }, [activeId, dispatch]);

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
    <div className="min-h-screen bg-cream flex flex-col font-sans text-charcoal">
      {/* Top Navbar */}
      <Navbar
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        onMenuClick={() => setIsSidebarOpen((prev) => !prev)}
      />

      {/* App Body with Sidebar + Main Content */}
      <div className="flex-1 flex max-w-[1920px] w-full mx-auto">
        {/* Navigation Sidebar */}
        <Sidebar mobileOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

        {/* Main Explorer Workspace */}
        <main className="flex-1 min-w-0 w-full px-3 pt-3 pb-[10px] sm:px-8 sm:pt-6 sm:pb-[10px] flex flex-col">
          {/* Breadcrumb Hierarchy */}
          <div className="mb-4 shrink-0">
            <Breadcrumbs breadcrumbs={breadcrumbs} currentFolderId={activeId} />
          </div>

          {/* Action Toolbar */}
          <div className="shrink-0">
            <Toolbar />
          </div>

          {/* Drag & Drop File Explorer Zone */}
          <DropZone>
            <FileList onUploadClick={handleUploadClick} />
          </DropZone>
        </main>
      </div>

      {/* Hidden File Picker Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={env.VITE_ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(',')}
        multiple
        onChange={handleFileInputChange}
        className="hidden"
        aria-label="Upload PDF Files"
      />

      {/* Dialog Modals */}
      <NewFolderDialog />
      <DeleteConfirmDialog />
      <TitleConfirmDialog />
      <ReviewFormDialog />
      <TexPreviewDialog />
      <StyleManagerDialog />

      {/* Floating Drawers & Docks */}
      <UploadDrawer />
      <JobPanel />
      <ActiveJobDock />
    </div>
  );
};
