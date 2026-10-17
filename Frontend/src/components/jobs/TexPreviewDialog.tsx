import React, { useState, useEffect } from 'react';
import { Copy, Download, Check, FileText } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeTexPreviewModal } from '@/store/slices/jobsSlice';
import { addToast } from '@/store/slices/uiSlice';
import { downloadJobTex } from '@/api/jobs';
import { Modal } from '@/components/common/Modal';
import { Button } from '@/components/common/Button';
import { Spinner } from '@/components/common/Spinner';

export const TexPreviewDialog: React.FC = () => {
  const dispatch = useAppDispatch();
  const activeJobId = useAppSelector((state) => state.jobs.activeTexPreviewJobId);
  const job = useAppSelector((state) => (activeJobId ? state.jobs.jobsById[activeJobId] : undefined));

  const [texContent, setTexContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    if (activeJobId) {
      downloadJobTex(activeJobId)
        .then((content) => {
          if (!ignore) {
            setTexContent(content);
            setIsLoading(false);
          }
        })
        .catch((err) => {
          if (!ignore) {
            setError(err instanceof Error ? err.message : 'Failed to retrieve .tex document');
            setIsLoading(false);
          }
        });
    }
    return () => {
      ignore = true;
    };
  }, [activeJobId]);

  const handleClose = () => {
    dispatch(closeTexPreviewModal());
  };

  const handleCopy = async () => {
    if (!texContent) return;
    try {
      await navigator.clipboard.writeText(texContent);
      setCopied(true);
      dispatch(
        addToast({
          type: 'success',
          message: 'LaTeX code copied to clipboard.',
        })
      );
      setTimeout(() => setCopied(false), 2000);
    } catch {
      dispatch(
        addToast({
          type: 'error',
          message: 'Clipboard permission denied.',
        })
      );
    }
  };

  const handleDownload = () => {
    if (!texContent) return;

    // Create a temporary Blob and download link
    const blob = new Blob([texContent], { type: 'text/x-tex;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    const filename = job?.file_id ? `citation_${job.file_id.slice(0, 8)}.tex` : 'citation.tex';
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Revoke object URL
    URL.revokeObjectURL(url);

    dispatch(
      addToast({
        type: 'success',
        message: `Downloaded "${filename}".`,
      })
    );
  };

  const isStandalone = job?.tex_mode === 'standalone';

  return (
    <Modal
      isOpen={!!activeJobId}
      onClose={handleClose}
      title="Generated LaTeX Citation (.tex)"
      description="Your verified bibliographic citation is ready for compile."
      maxWidth="xl"
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="py-16 flex flex-col items-center justify-center">
            <Spinner size="md" label="Loading .tex output" />
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-red-50 text-red-700 text-xs font-sans">
            {error}
          </div>
        ) : (
          <>
            {/* Format Hint */}
            <div className="p-3 rounded-xl bg-cream-100 border border-border-light text-[11px] font-mono text-charcoal/70 flex items-start gap-2">
              <FileText className="w-3.5 h-3.5 text-indigo-brand shrink-0 mt-0.5" />
              <div>
                {isStandalone ? (
                  <span>
                    <strong>Standalone Document:</strong> Includes full document preamble. Note: requires the <code>\usepackage&#123;hyperref&#125;</code> package.
                  </span>
                ) : (
                  <span>
                    <strong>Bibliography Fragment:</strong> Place this snippet inside your paper&rsquo;s <code>\begin&#123;thebibliography&#125; ... \end&#123;thebibliography&#125;</code> environment.
                  </span>
                )}
              </div>
            </div>

            {/* Read-only Monospace Preview Area */}
            <div className="relative rounded-xl border border-charcoal-800 bg-charcoal-900 text-cream p-4 font-mono text-xs overflow-x-auto max-h-80 select-text leading-relaxed">
              <pre className="m-0 font-mono whitespace-pre-wrap">{texContent}</pre>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-2">
              <div className="text-[11px] font-mono text-charcoal/40 uppercase">
                {texContent.length} characters
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  className="gap-1.5"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleDownload}
                  className="gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download .tex</span>
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
};
