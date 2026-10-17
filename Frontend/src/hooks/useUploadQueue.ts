import { useEffect, useRef, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  updateProgress,
  setItemStatus,
  cancelUploadItem,
  retryUploadItem,
  clearCompleted,
  setDrawerOpen,
} from '@/store/slices/uploadSlice';
import { optimisticAddFile } from '@/store/slices/explorerSlice';
import { addToast } from '@/store/slices/uiSlice';
import { uploadFileWithProgress } from '@/api/files';
import { getErrorMessage } from '@/api/errors';
import { env } from '@/lib/env';

export function useUploadQueue() {
  const dispatch = useAppDispatch();
  const { items, isDrawerOpen, isMinimized } = useAppSelector((state) => state.upload);
  const currentFolderId = useAppSelector((state) => state.explorer.currentFolderId);

  const abortControllersRef = useRef<Record<string, { abort?: () => void }>>({});
  const activeUploadsCountRef = useRef<number>(0);

  // Guard against navigating away or refreshing while uploads are active
  useEffect(() => {
    const hasActiveUploads = items.some((i) => i.status === 'uploading' || i.status === 'queued');

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasActiveUploads) {
        e.preventDefault();
        e.returnValue = 'Uploads are currently in progress. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [items]);

  // Queue runner effect
  useEffect(() => {
    const uploadingItems = items.filter((i) => i.status === 'uploading');
    activeUploadsCountRef.current = uploadingItems.length;

    const availableSlots = env.VITE_UPLOAD_CONCURRENCY - uploadingItems.length;
    if (availableSlots <= 0) return;

    const queuedItems = items.filter((i) => i.status === 'queued');
    const itemsToStart = queuedItems.slice(0, availableSlots);

    itemsToStart.forEach((item) => {
      const itemId = item.id;
      const abortHolder: { abort?: () => void } = {};
      abortControllersRef.current[itemId] = abortHolder;

      // Mark as uploading
      dispatch(updateProgress({ id: itemId, progress: 1 }));

      uploadFileWithProgress(
        item.file,
        item.folderId,
        (percentage) => {
          dispatch(updateProgress({ id: itemId, progress: percentage }));
        },
        abortHolder
      )
        .then((uploadedFile) => {
          dispatch(setItemStatus({ id: itemId, status: 'done' }));
          dispatch(
            addToast({
              type: 'success',
              message: `Uploaded "${item.name}" successfully.`,
            })
          );

          // If current open folder matches target folder, optimistically add to explorer
          if (currentFolderId === item.folderId || (currentFolderId === 'root' && item.folderId === 'root')) {
            dispatch(optimisticAddFile(uploadedFile));
          }
        })
        .catch((error) => {
          if (item.status === 'canceled') return;
          const msg = getErrorMessage(error);
          dispatch(setItemStatus({ id: itemId, status: 'error', errorMessage: msg }));
          dispatch(
            addToast({
              type: 'error',
              message: `Failed to upload "${item.name}": ${msg}`,
            })
          );
        })
        .finally(() => {
          delete abortControllersRef.current[itemId];
        });
    });
  }, [items, dispatch, currentFolderId]);

  const cancelUpload = useCallback(
    (id: string) => {
      const abortObj = abortControllersRef.current[id];
      if (abortObj?.abort) {
        abortObj.abort();
      }
      dispatch(cancelUploadItem(id));
    },
    [dispatch]
  );

  const retryUpload = useCallback(
    (id: string) => {
      dispatch(retryUploadItem(id));
    },
    [dispatch]
  );

  const clearDone = useCallback(() => {
    dispatch(clearCompleted());
  }, [dispatch]);

  const setOpen = useCallback(
    (open: boolean) => {
      dispatch(setDrawerOpen(open));
    },
    [dispatch]
  );

  return {
    items,
    isDrawerOpen,
    isMinimized,
    cancelUpload,
    retryUpload,
    clearDone,
    setOpen,
  };
}
