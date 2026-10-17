import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { UploadQueueItem, UploadStatus } from '@/types/api';

export interface UploadState {
  items: UploadQueueItem[];
  isDrawerOpen: boolean;
  isMinimized: boolean;
}

const initialState: UploadState = {
  items: [],
  isDrawerOpen: false,
  isMinimized: false,
};

export const uploadSlice = createSlice({
  name: 'upload',
  initialState,
  reducers: {
    addUploads(state, action: PayloadAction<UploadQueueItem[]>) {
      state.items.push(...action.payload);
      state.isDrawerOpen = true;
      state.isMinimized = false;
    },
    updateProgress(state, action: PayloadAction<{ id: string; progress: number }>) {
      const item = state.items.find((i) => i.id === action.payload.id);
      if (item && item.status !== 'canceled') {
        item.progress = action.payload.progress;
        item.status = 'uploading';
      }
    },
    setItemStatus(state, action: PayloadAction<{ id: string; status: UploadStatus; errorMessage?: string }>) {
      const item = state.items.find((i) => i.id === action.payload.id);
      if (item) {
        item.status = action.payload.status;
        if (action.payload.errorMessage) {
          item.errorMessage = action.payload.errorMessage;
        }
        if (action.payload.status === 'done') {
          item.progress = 100;
        }
      }
    },
    cancelUploadItem(state, action: PayloadAction<string>) {
      const item = state.items.find((i) => i.id === action.payload);
      if (item && (item.status === 'queued' || item.status === 'uploading')) {
        item.status = 'canceled';
        item.errorMessage = 'Canceled';
      }
    },
    retryUploadItem(state, action: PayloadAction<string>) {
      const item = state.items.find((i) => i.id === action.payload);
      if (item && (item.status === 'error' || item.status === 'canceled')) {
        item.status = 'queued';
        item.progress = 0;
        item.errorMessage = undefined;
      }
    },
    clearCompleted(state) {
      state.items = state.items.filter((i) => i.status === 'queued' || i.status === 'uploading');
      if (state.items.length === 0) {
        state.isDrawerOpen = false;
      }
    },
    toggleDrawer(state) {
      state.isDrawerOpen = !state.isDrawerOpen;
    },
    setDrawerOpen(state, action: PayloadAction<boolean>) {
      state.isDrawerOpen = action.payload;
    },
    toggleMinimized(state) {
      state.isMinimized = !state.isMinimized;
    },
  },
});

export const {
  addUploads,
  updateProgress,
  setItemStatus,
  cancelUploadItem,
  retryUploadItem,
  clearCompleted,
  toggleDrawer,
  setDrawerOpen,
  toggleMinimized,
} = uploadSlice.actions;

export default uploadSlice.reducer;
