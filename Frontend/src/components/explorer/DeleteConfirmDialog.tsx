import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeDeleteDialog, addToast } from '@/store/slices/uiSlice';
import { optimisticRemoveFile, optimisticRemoveFolder } from '@/store/slices/explorerSlice';
import { removeJobsForFile } from '@/store/slices/jobsSlice';
import { deleteFile } from '@/api/files';
import { deleteFolder } from '@/api/folders';
import { Modal } from '@/components/common/Modal';
import { Button } from '@/components/common/Button';
import { getErrorMessage } from '@/api/errors';

export const DeleteConfirmDialog: React.FC = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const deleteTarget = useAppSelector((state) => state.ui.deleteTarget);
  const currentFolderId = useAppSelector((state) => state.explorer.currentFolderId);
  const breadcrumbs = useAppSelector((state) => state.explorer.folderData?.breadcrumbs);

  const [isDeleting, setIsDeleting] = useState(false);

  const handleClose = () => {
    dispatch(closeDeleteDialog());
  };

  if (!deleteTarget) return null;

  const isFolder = deleteTarget.type === 'folder';

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      if (isFolder) {
        // Optimistic removal
        dispatch(optimisticRemoveFolder(deleteTarget.id));
        await deleteFolder(deleteTarget.id);

        dispatch(
          addToast({
            type: 'success',
            message: `Deleted folder "${deleteTarget.name}".`,
          })
        );

        // If currently viewing the folder that was deleted, navigate up to parent
        if (currentFolderId === deleteTarget.id) {
          if (breadcrumbs && breadcrumbs.length > 1) {
            const parent = breadcrumbs[breadcrumbs.length - 2];
            navigate(parent.id === 'root' ? '/' : `/folders/${parent.id}`);
          } else {
            navigate('/');
          }
        }
      } else {
        // File deletion
        dispatch(optimisticRemoveFile(deleteTarget.id));
        dispatch(removeJobsForFile(deleteTarget.id));
        await deleteFile(deleteTarget.id);

        dispatch(
          addToast({
            type: 'success',
            message: `Deleted file "${deleteTarget.name}".`,
          })
        );
      }
      handleClose();
    } catch (err) {
      dispatch(
        addToast({
          type: 'error',
          message: `Failed to delete ${deleteTarget.name}: ${getErrorMessage(err)}`,
        })
      );
      // In a real application we would re-fetch to roll back
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Modal
      isOpen={!!deleteTarget}
      onClose={handleClose}
      title={isFolder ? 'Delete Folder' : 'Delete File'}
    >
      <div className="space-y-4">
        {isFolder ? (
          <p className="text-sm text-charcoal/80 font-sans leading-relaxed">
            Delete the folder <strong className="text-charcoal-900 font-semibold">{deleteTarget.name}</strong> and{' '}
            <strong className="text-red-600 font-semibold">everything inside it</strong> (all subfolders and files)?
            This cannot be undone.
          </p>
        ) : (
          <p className="text-sm text-charcoal/80 font-sans leading-relaxed">
            Delete <strong className="text-charcoal-900 font-semibold">{deleteTarget.name}</strong>? This cannot be undone.
          </p>
        )}

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-light">
          <Button
            type="button"
            variant="ghost"
            onClick={handleClose}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleDelete}
            isLoading={isDeleting}
          >
            {isFolder ? 'Delete folder' : 'Delete'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
