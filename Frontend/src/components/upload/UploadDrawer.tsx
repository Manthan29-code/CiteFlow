import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  ChevronDown,
  ChevronUp,
  X,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { useUploadQueue } from '@/hooks/useUploadQueue';
import { useAppDispatch } from '@/store/hooks';
import { toggleMinimized } from '@/store/slices/uploadSlice';
import { formatBytes } from '@/lib/format';
import { cn } from '@/lib/utils';

export const UploadDrawer: React.FC = () => {
  const dispatch = useAppDispatch();
  const { items, isDrawerOpen, isMinimized, cancelUpload, retryUpload, clearDone, setOpen } =
    useUploadQueue();

  if (!isDrawerOpen || items.length === 0) return null;

  const activeCount = items.filter((i) => i.status === 'uploading' || i.status === 'queued').length;
  const completedCount = items.filter((i) => i.status === 'done').length;

  return (
    <div
      aria-live="polite"
      className="fixed bottom-5 right-5 z-40 w-full max-w-md shadow-2xl rounded-2xl overflow-hidden border border-border-light bg-white text-charcoal font-sans"
    >
      {/* Drawer Header */}
      <div className="bg-charcoal-900 text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Upload className="w-4 h-4 text-indigo-300" />
          <span className="font-mono text-xs uppercase tracking-wider font-semibold">
            Upload Queue ({activeCount} active, {completedCount} done)
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => dispatch(toggleMinimized())}
            className="p-1 rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors"
            title={isMinimized ? 'Expand' : 'Minimize'}
          >
            {isMinimized ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors"
            title="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Drawer Content */}
      <AnimatePresence>
        {!isMinimized && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="max-h-72 overflow-y-auto divide-y divide-border-light bg-cream-50"
          >
            {items.map((item) => {
              const isUploading = item.status === 'uploading';
              const isDone = item.status === 'done';
              const isError = item.status === 'error';
              const isCanceled = item.status === 'canceled';
              const isQueued = item.status === 'queued';

              return (
                <div key={item.id} className="p-3 flex flex-col gap-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 truncate max-w-[240px]">
                      <FileText className="w-3.5 h-3.5 text-indigo-brand shrink-0" />
                      <span className="font-medium text-charcoal-900 truncate" title={item.name}>
                        {item.name}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[11px] font-mono text-charcoal/50">
                        {formatBytes(item.sizeBytes)}
                      </span>

                      {/* Cancel button */}
                      {(isUploading || isQueued) && (
                        <button
                          onClick={() => cancelUpload(item.id)}
                          className="text-charcoal/40 hover:text-red-600 transition-colors"
                          title="Cancel upload"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}

                      {/* Retry button */}
                      {(isError || isCanceled) && (
                        <button
                          onClick={() => retryUpload(item.id)}
                          className="text-indigo-brand hover:text-indigo-hover transition-colors flex items-center gap-1 font-mono text-[11px]"
                          title="Retry upload"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Retry</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Progress Bar & Status */}
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-1.5 rounded-full bg-border-light overflow-hidden">
                      <div
                        className={cn(
                          'h-full transition-all duration-200 rounded-full',
                          isDone && 'bg-emerald-500',
                          isError && 'bg-red-500',
                          isCanceled && 'bg-charcoal/30',
                          (isUploading || isQueued) && 'bg-indigo-brand'
                        )}
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                    <span className="font-mono text-[10px] w-9 text-right text-charcoal/60">
                      {isDone ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 inline" />
                      ) : isError ? (
                        <AlertCircle className="w-3.5 h-3.5 text-red-600 inline" />
                      ) : (
                        `${item.progress}%`
                      )}
                    </span>
                  </div>

                  {/* Error reason if present */}
                  {isError && item.errorMessage && (
                    <div className="text-[11px] text-red-600 font-sans mt-0.5 truncate" title={item.errorMessage}>
                      {item.errorMessage}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Footer actions */}
            <div className="p-2.5 bg-white border-t border-border-light flex items-center justify-between text-xs">
              <span className="text-[11px] text-charcoal/50 font-mono">
                Concurrent limit: 2
              </span>
              <button
                onClick={clearDone}
                className="text-xs text-indigo-brand hover:underline font-medium"
              >
                Clear finished
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
