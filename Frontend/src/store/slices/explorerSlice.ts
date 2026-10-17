import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { FolderDetailResponse, FileItem, Folder } from '@/types/api';
import { getRootFolder, getFolderDetails } from '@/api/folders';
import { ApiError, getErrorMessage } from '@/api/errors';
import { env } from '@/lib/env';

export interface ExplorerState {
  currentFolderId: string;
  folderData: FolderDetailResponse | null;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  isNotFound: boolean;
  selectedFileId: string | null;
  searchQuery: string;
  viewMode: 'list' | 'grid';
}

const initialState: ExplorerState = {
  currentFolderId: 'root',
  folderData: null,
  isLoading: true,
  isLoadingMore: false,
  error: null,
  isNotFound: false,
  selectedFileId: null,
  searchQuery: '',
  viewMode: 'list',
};

export const fetchFolder = createAsyncThunk(
  'explorer/fetchFolder',
  async (folderId: string = 'root', { rejectWithValue }) => {
    try {
      if (folderId === 'root' || !folderId) {
        return await getRootFolder({ limit: env.VITE_PAGE_SIZE });
      } else {
        return await getFolderDetails(folderId, { limit: env.VITE_PAGE_SIZE });
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return rejectWithValue({ isNotFound: true, message: 'Folder not found.' });
      }
      return rejectWithValue({ isNotFound: false, message: getErrorMessage(error) });
    }
  }
);

export const loadMoreFolderItems = createAsyncThunk(
  'explorer/loadMoreFolderItems',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = (getState() as { explorer: ExplorerState }).explorer;
      const cursor = state.folderData?.next_cursor;
      if (!cursor) return null;

      const folderId = state.currentFolderId;
      if (folderId === 'root') {
        return await getRootFolder({ limit: env.VITE_PAGE_SIZE, cursor });
      } else {
        return await getFolderDetails(folderId, { limit: env.VITE_PAGE_SIZE, cursor });
      }
    } catch (error) {
      return rejectWithValue(getErrorMessage(error));
    }
  }
);

export const explorerSlice = createSlice({
  name: 'explorer',
  initialState,
  reducers: {
    setCurrentFolderId(state, action: PayloadAction<string>) {
      state.currentFolderId = action.payload;
    },
    setSelectedFileId(state, action: PayloadAction<string | null>) {
      state.selectedFileId = action.payload;
    },
    setSearchQuery(state, action: PayloadAction<string>) {
      state.searchQuery = action.payload;
    },
    setViewMode(state, action: PayloadAction<'list' | 'grid'>) {
      state.viewMode = action.payload;
    },
    optimisticRemoveFile(state, action: PayloadAction<string>) {
      if (state.folderData) {
        state.folderData.files = state.folderData.files.filter((f) => f.id !== action.payload);
      }
      if (state.selectedFileId === action.payload) {
        state.selectedFileId = null;
      }
    },
    optimisticRemoveFolder(state, action: PayloadAction<string>) {
      if (state.folderData) {
        state.folderData.folders = state.folderData.folders.filter((f) => f.id !== action.payload);
      }
    },
    optimisticAddFolder(state, action: PayloadAction<Folder>) {
      if (state.folderData) {
        state.folderData.folders = [action.payload, ...state.folderData.folders];
      }
    },
    optimisticAddFile(state, action: PayloadAction<FileItem>) {
      if (state.folderData) {
        state.folderData.files = [action.payload, ...state.folderData.files];
      }
    },
    resetExplorer(state) {
      state.folderData = null;
      state.selectedFileId = null;
      state.error = null;
      state.isNotFound = false;
      state.isLoading = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchFolder.pending, (state, action) => {
        state.isLoading = true;
        state.error = null;
        state.isNotFound = false;
        state.currentFolderId = action.meta.arg || 'root';
      })
      .addCase(fetchFolder.fulfilled, (state, action) => {
        state.isLoading = false;
        state.folderData = action.payload;
        state.error = null;
        state.isNotFound = false;
      })
      .addCase(fetchFolder.rejected, (state, action) => {
        state.isLoading = false;
        const payload = action.payload as { isNotFound?: boolean; message?: string } | undefined;
        state.isNotFound = !!payload?.isNotFound;
        state.error = payload?.message || 'Failed to load folder';
      })
      .addCase(loadMoreFolderItems.pending, (state) => {
        state.isLoadingMore = true;
      })
      .addCase(loadMoreFolderItems.fulfilled, (state, action) => {
        state.isLoadingMore = false;
        if (action.payload && state.folderData) {
          // Merge newly fetched folders and files without duplicates
          const newFolderIds = new Set(action.payload.folders.map((f) => f.id));
          const newFileIds = new Set(action.payload.files.map((f) => f.id));

          state.folderData.folders = [
            ...state.folderData.folders.filter((f) => !newFolderIds.has(f.id)),
            ...action.payload.folders,
          ];
          state.folderData.files = [
            ...state.folderData.files.filter((f) => !newFileIds.has(f.id)),
            ...action.payload.files,
          ];
          state.folderData.next_cursor = action.payload.next_cursor;
        }
      })
      .addCase(loadMoreFolderItems.rejected, (state) => {
        state.isLoadingMore = false;
      });
  },
});

export const {
  setCurrentFolderId,
  setSelectedFileId,
  setSearchQuery,
  setViewMode,
  optimisticRemoveFile,
  optimisticRemoveFolder,
  optimisticAddFolder,
  optimisticAddFile,
  resetExplorer,
} = explorerSlice.actions;

export default explorerSlice.reducer;
