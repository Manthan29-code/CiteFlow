import React, { useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeNewFolderModal, addToast } from '@/store/slices/uiSlice';
import { optimisticAddFolder } from '@/store/slices/explorerSlice';
import { createFolder } from '@/api/folders';
import { Modal } from '@/components/common/Modal';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import { validateFolderName } from '@/lib/format';
import { ApiError, getErrorMessage } from '@/api/errors';

export const NewFolderDialog: React.FC = () => {
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector((state) => state.ui.isNewFolderModalOpen);
  const currentFolder = useAppSelector((state) => state.explorer.folderData?.folder);

  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleClose = () => {
    setName('');
    setError(null);
    dispatch(closeNewFolderModal());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Client-side validation according to spec
    const validation = validateFolderName(name);
    if (!validation.isValid) {
      setError(validation.error || 'Invalid folder name.');
      return;
    }

    if (!currentFolder?.id) {
      setError('Cannot determine parent folder.');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await createFolder({
        name: validation.normalized,
        parent_id: currentFolder.id,
      });

      dispatch(optimisticAddFolder(created));
      dispatch(
        addToast({
          type: 'success',
          message: `Created folder "${created.name}".`,
        })
      );
      handleClose();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'name_conflict') {
          setError('A folder or file with this name already exists here.');
        } else if (err.code === 'folder_too_deep') {
          setError("Folders can't be nested this deeply.");
        } else {
          setError(getErrorMessage(err));
        }
      } else {
        setError(getErrorMessage(err));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New Folder"
      description="Organize your research documents into nested folders."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Folder Name"
          placeholder="e.g. Transformers & Attention Papers"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (error) setError(null);
          }}
          error={error || undefined}
          autoFocus
          disabled={isSubmitting}
          helperText="Max 120 characters, no slashes or special characters."
        />

        <div className="flex items-center justify-end gap-3 pt-3">
          <Button
            type="button"
            variant="ghost"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
          >
            Create Folder
          </Button>
        </div>
      </form>
    </Modal>
  );
};
