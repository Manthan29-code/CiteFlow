import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Folder as FolderIcon,
  FileText,
  MoreVertical,
  ExternalLink,
  Trash2,
  Sparkles,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openDeleteDialog, addToast } from '@/store/slices/uiSlice';
import { setSelectedFileId } from '@/store/slices/explorerSlice';
import { openTexPreviewModal } from '@/store/slices/jobsSlice';
import { StatusBadge } from '@/components/jobs/StatusBadge';
import { GenerateButton } from '@/components/jobs/GenerateButton';
import { getSignedUrl } from '@/api/files';
import { formatBytes, formatDate } from '@/lib/format';
import { getErrorMessage } from '@/api/errors';
import { Folder, FileItem } from '@/types/api';
import { cn } from '@/lib/utils';

export interface FileRowProps {
  item: {
    type: 'folder' | 'file';
    data: Folder | FileItem;
  };
}

export const FileRow: React.FC<FileRowProps> = ({ item }) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const selectedFileId = useAppSelector((state) => state.explorer.selectedFileId);

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const isFolder = item.type === 'folder';
  const folder = isFolder ? (item.data as Folder) : null;
  const file = !isFolder ? (item.data as FileItem) : null;
  const id = isFolder ? folder!.id : file!.id;
  const name = isFolder ? folder!.name : file!.name;
  const isSelected = !isFolder && selectedFileId === file!.id;

  const job = useAppSelector((state) => (!isFolder && file ? state.jobs.jobsByFileId[file.id] : undefined));

  // Close context menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuOpen]);

  // Navigate folder
  const handleOpenFolder = () => {
    if (isFolder) {
      navigate(`/folders/${folder!.id}`);
    }
  };

  // Open PDF securely via signed URL
  const handleOpenPdf = async (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!file) return;

    // Open blank tab synchronously to satisfy popup blocker rules
    const w = window.open('', '_blank');
    if (w) {
      w.opener = null;
    }

    try {
      const response = await getSignedUrl(file.id);
      if (w) {
        w.location.href = response.url;
      } else {
        dispatch(
          addToast({
            type: 'error',
            message: 'Please allow pop-ups to open the PDF.',
          })
        );
      }
    } catch (err) {
      if (w) w.close();
      dispatch(
        addToast({
          type: 'error',
          message: `Could not open PDF: ${getErrorMessage(err)}`,
        })
      );
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpen(false);
    dispatch(
      openDeleteDialog({
        type: isFolder ? 'folder' : 'file',
        id,
        name,
      })
    );
  };

  const handleRowClick = () => {
    if (!isFolder) {
      dispatch(setSelectedFileId(file!.id));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (isFolder) {
        handleOpenFolder();
      } else {
        handleOpenPdf();
      }
    }
  };

  return (
    <tr
      tabIndex={0}
      onClick={handleRowClick}
      onDoubleClick={isFolder ? handleOpenFolder : handleOpenPdf}
      onKeyDown={handleKeyDown}
      className={cn(
        'group border-b border-border-light hover:bg-cream-200/70 transition-colors select-none cursor-pointer focus-visible:outline-none focus-visible:bg-indigo-50/50',
        isSelected && 'bg-indigo-50/80 border-indigo-200'
      )}
    >
      {/* Name Column */}
      <td className="py-3 px-4 flex items-center gap-3">
        {isFolder ? (
          <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-brand shrink-0 group-hover:scale-105 transition-transform">
            <FolderIcon className="w-4 h-4 fill-indigo-brand/20" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center text-red-600 shrink-0 group-hover:scale-105 transition-transform">
            <FileText className="w-4 h-4" />
          </div>
        )}

        <div className="flex flex-col min-w-0">
          <span className="text-xs sm:text-sm font-medium text-charcoal-900 truncate" title={name}>
            {name}
          </span>
          <span className="text-[11px] font-mono text-charcoal/40 sm:hidden">
            {isFolder ? 'Folder' : formatBytes(file!.size_bytes)}
          </span>
        </div>
      </td>

      {/* Size Column */}
      <td className="py-3 px-4 hidden sm:table-cell text-xs font-mono text-charcoal/60">
        {isFolder ? '—' : formatBytes(file!.size_bytes)}
      </td>

      {/* Created Date Column */}
      <td className="py-3 px-4 hidden md:table-cell text-xs font-mono text-charcoal/60">
        {formatDate(item.data.created_at)}
      </td>

      {/* Citation Column */}
      <td className="py-3 px-4 hidden sm:table-cell text-center">
        {isFolder ? (
          <span className="text-xs font-mono text-charcoal/30">—</span>
        ) : (
          <div className="flex items-center justify-center gap-2">
            {job && <StatusBadge job={job} />}
            {(!job || ['succeeded', 'unresolved', 'failed', 'canceled', 'expired'].includes(job.status)) && (
              <GenerateButton fileId={file!.id} fileName={file!.name} />
            )}
          </div>
        )}
      </td>

      {/* Actions Kebab Menu */}
      <td className="py-3 px-4 text-right">
        <div className="relative inline-block text-left" ref={menuRef}>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen(!menuOpen);
            }}
            aria-label={`Actions for ${name}`}
            className="p-1.5 rounded-lg text-charcoal/40 hover:text-charcoal hover:bg-black/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 z-30 mt-1 w-44 rounded-xl bg-white border border-border-light shadow-lg py-1 text-xs font-sans text-charcoal-800 animate-in fade-in zoom-in-95 duration-100">
              {!isFolder ? (
                <>
                  <button
                    onClick={handleOpenPdf}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-cream-200 transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-indigo-brand" />
                    <span>Open PDF</span>
                  </button>

                  {job?.status === 'succeeded' && (
                    <button
                      onClick={() => {
                        setMenuOpen(false);
                        dispatch(openTexPreviewModal(job.id));
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-cream-200 transition-colors text-indigo-brand font-medium"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>View .tex</span>
                    </button>
                  )}

                  <button
                    onClick={handleDelete}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete</span>
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleOpenFolder}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-cream-200 transition-colors"
                  >
                    <FolderIcon className="w-3.5 h-3.5 text-indigo-brand" />
                    <span>Open</span>
                  </button>
                  <button
                    onClick={handleDelete}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete</span>
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </td>
    </tr>
  );
};
