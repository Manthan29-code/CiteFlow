import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { JobResponse } from '@/types/api';

export interface JobsState {
  jobsById: Record<string, JobResponse>;
  jobsByFileId: Record<string, JobResponse>;
  isStartingJobByFileId: Record<string, boolean>;
  activeJobDrawerJobId: string | null;
  activeTitleConfirmJobId: string | null;
  activeReviewJobId: string | null;
  activeTexPreviewJobId: string | null;
}

const initialState: JobsState = {
  jobsById: {},
  jobsByFileId: {},
  isStartingJobByFileId: {},
  activeJobDrawerJobId: null,
  activeTitleConfirmJobId: null,
  activeReviewJobId: null,
  activeTexPreviewJobId: null,
};

export const jobsSlice = createSlice({
  name: 'jobs',
  initialState,
  reducers: {
    setJob(state, action: PayloadAction<JobResponse>) {
      const job = action.payload;
      state.jobsById[job.id] = job;
      state.jobsByFileId[job.file_id] = job;

      // Automatically sync active modal triggers if this job is currently open
      if (state.activeJobDrawerJobId === job.id) {
        // state updated
      }
    },
    setStartingJob(state, action: PayloadAction<{ fileId: string; isStarting: boolean }>) {
      state.isStartingJobByFileId[action.payload.fileId] = action.payload.isStarting;
    },
    openJobDrawer(state, action: PayloadAction<string>) {
      state.activeJobDrawerJobId = action.payload;
    },
    closeJobDrawer(state) {
      state.activeJobDrawerJobId = null;
    },
    openTitleConfirmModal(state, action: PayloadAction<string>) {
      state.activeTitleConfirmJobId = action.payload;
    },
    closeTitleConfirmModal(state) {
      state.activeTitleConfirmJobId = null;
    },
    openReviewModal(state, action: PayloadAction<string>) {
      state.activeReviewJobId = action.payload;
    },
    closeReviewModal(state) {
      state.activeReviewJobId = null;
    },
    openTexPreviewModal(state, action: PayloadAction<string>) {
      state.activeTexPreviewJobId = action.payload;
    },
    closeTexPreviewModal(state) {
      state.activeTexPreviewJobId = null;
    },
    removeJobsForFile(state, action: PayloadAction<string>) {
      const fileId = action.payload;
      delete state.jobsByFileId[fileId];
      Object.keys(state.jobsById).forEach((id) => {
        if (state.jobsById[id]?.file_id === fileId) {
          delete state.jobsById[id];
        }
      });
    },
  },
});

export const {
  setJob,
  setStartingJob,
  openJobDrawer,
  closeJobDrawer,
  openTitleConfirmModal,
  closeTitleConfirmModal,
  openReviewModal,
  closeReviewModal,
  openTexPreviewModal,
  closeTexPreviewModal,
  removeJobsForFile,
} = jobsSlice.actions;

export default jobsSlice.reducer;
