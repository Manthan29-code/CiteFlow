import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import explorerReducer from './slices/explorerSlice';
import uploadReducer from './slices/uploadSlice';
import uiReducer from './slices/uiSlice';
import jobsReducer from './slices/jobsSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    explorer: explorerReducer,
    upload: uploadReducer,
    ui: uiReducer,
    jobs: jobsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore File instances and XHR objects in upload queue
        ignoredActions: ['upload/addUploads'],
        ignoredActionPaths: ['payload', 'meta.arg'],
        ignoredPaths: ['upload.items'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
