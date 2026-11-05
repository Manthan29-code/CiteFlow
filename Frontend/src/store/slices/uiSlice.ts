import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface ToastItem {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

export interface DeleteTarget {
  type: 'file' | 'folder';
  id: string;
  name: string;
}

export interface UIState {
  isNewFolderModalOpen: boolean;
  isStyleManagerModalOpen: boolean;
  deleteTarget: DeleteTarget | null;
  toasts: ToastItem[];
}

const initialState: UIState = {
  isNewFolderModalOpen: false,
  isStyleManagerModalOpen: false,
  deleteTarget: null,
  toasts: [],
};

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    openNewFolderModal(state) {
      state.isNewFolderModalOpen = true;
    },
    closeNewFolderModal(state) {
      state.isNewFolderModalOpen = false;
    },
    openStyleManagerModal(state) {
      state.isStyleManagerModalOpen = true;
    },
    closeStyleManagerModal(state) {
      state.isStyleManagerModalOpen = false;
    },
    openDeleteDialog(state, action: PayloadAction<DeleteTarget>) {
      state.deleteTarget = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteTarget = null;
    },
    addToast(state, action: PayloadAction<Omit<ToastItem, 'id'>>) {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      state.toasts.push({ ...action.payload, id });
    },
    removeToast(state, action: PayloadAction<string>) {
      state.toasts = state.toasts.filter((t) => t.id !== action.payload);
    },
  },
});

export const {
  openNewFolderModal,
  closeNewFolderModal,
  openStyleManagerModal,
  closeStyleManagerModal,
  openDeleteDialog,
  closeDeleteDialog,
  addToast,
  removeToast,
} = uiSlice.actions;

export default uiSlice.reducer;
