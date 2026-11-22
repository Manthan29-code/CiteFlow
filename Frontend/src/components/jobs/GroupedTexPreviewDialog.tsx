import React, { useState, useEffect, useRef } from 'react';
import { Copy, Download, Check, Wand2, ChevronDown, Loader2 } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeGroupedTexModal, setJobs } from '@/store/slices/jobsSlice';
import { addToast } from '@/store/slices/uiSlice';
import { downloadFolderTex, transformFolderStyle } from '@/api/jobs';
import { getErrorMessage } from '@/api/errors';
import { Modal } from '@/components/common/Modal';
import { Button } from '@/components/common/Button';
import { Spinner } from '@/components/common/Spinner';

const cleanGroupedCitationCode = (raw: string): string => {
  if (!raw) return '';
  // Extract all individual \bibitem citation snippets and separate with an empty line
  const matches = raw.match(/\\bibitem[\s\S]*?(?=(?:\\bibitem|\\end\{thebibliography\}|\\end\{document\}|$))/g);
  if (matches && matches.length > 0) {
    return matches.map((m) => m.trim()).filter(Boolean).join('\n\n');
  }
  return raw.trim();
};

export const GroupedTexPreviewDialog: React.FC = () => {
  const dispatch = useAppDispatch();
  const folderId = useAppSelector((state) => state.jobs.activeGroupedTexFolderId);
  const currentFolder = useAppSelector((state) => state.explorer.folderData?.folder);
  const { styles, selectedStyleId } = useAppSelector((state) => state.styles);

  const [texContent, setTexContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Style transform state
  const [transformMenuOpen, setTransformMenuOpen] = useState<boolean>(false);
  const [isTransforming, setIsTransforming] = useState<boolean>(false);
  const transformMenuRef = useRef<HTMLDivElement>(null);

  // Close transform dropdown on outside click
  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (transformMenuRef.current && !transformMenuRef.current.contains(e.target as Node)) {
        setTransformMenuOpen(false);
      }
    };
    if (transformMenuOpen) {
      document.addEventListener('mousedown', handleOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutside);
    };
  }, [transformMenuOpen]);

  useEffect(() => {
    let ignore = false;
    if (folderId) {
      setIsLoading(true);
      setError(null);

      const syncAndDownload = async () => {
        try {
          if (selectedStyleId) {
            // Unify all folder jobs to the globally selected style in DB & Redux
            const updatedJobs = await transformFolderStyle(folderId, selectedStyleId);
            if (!ignore) {
              dispatch(setJobs(updatedJobs));
            }
          }
          const content = await downloadFolderTex(folderId, selectedStyleId);
          if (!ignore) {
            setTexContent(cleanGroupedCitationCode(content));
            setIsLoading(false);
          }
        } catch (err) {
          if (!ignore) {
            setError(err instanceof Error ? err.message : 'Failed to retrieve grouped .tex document');
            setIsLoading(false);
          }
        }
      };

      syncAndDownload();
    }
    return () => {
      ignore = true;
    };
  }, [folderId, selectedStyleId, dispatch]);

  const handleClose = () => {
    dispatch(closeGroupedTexModal());
  };

  const handleCopy = async () => {
    if (!texContent) return;
    try {
      await navigator.clipboard.writeText(texContent);
      setCopied(true);
      dispatch(
        addToast({
          type: 'success',
          message: 'Grouped LaTeX code copied to clipboard.',
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

    const blob = new Blob([texContent], { type: 'text/x-tex;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    const folderName = currentFolder?.name ? currentFolder.name.replace(/[^a-zA-Z0-9_\-]/g, '_') : 'folder';
    const filename = `${folderName}_citations.tex`;
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);

    dispatch(
      addToast({
        type: 'success',
        message: `Downloaded "${filename}".`,
      })
    );
  };

  const handleTransform = async (styleId: string, styleName: string) => {
    if (!folderId || isTransforming) return;
    setIsTransforming(true);
    setTransformMenuOpen(false);
    try {
      const updatedJobs = await transformFolderStyle(folderId, styleId);
      dispatch(setJobs(updatedJobs));
      const updatedTex = await downloadFolderTex(folderId, styleId);
      setTexContent(cleanGroupedCitationCode(updatedTex));
      dispatch(
        addToast({
          type: 'success',
          message: `All folder citations transformed to "${styleName}".`,
        })
      );
    } catch (err: unknown) {
      dispatch(
        addToast({
          type: 'error',
          message: `Failed to transform style: ${getErrorMessage(err)}`,
        })
      );
    } finally {
      setIsTransforming(false);
    }
  };

  return (
    <Modal
      isOpen={!!folderId}
      onClose={handleClose}
      title="Grouped LaTeX Citations"
      maxWidth="3xl"
    >
      <div className="space-y-3 sm:space-y-4">
        {isLoading ? (
          <div className="py-16 flex flex-col items-center justify-center">
            <Spinner size="md" label="Loading grouped .tex output" />
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-red-50 text-red-700 text-xs font-sans">
            {error}
          </div>
        ) : (
          <>
            {/* Read-only Monospace Preview Area */}
            <div className="relative rounded-xl border border-charcoal-800 bg-charcoal-900 text-cream p-3 sm:p-4 font-mono text-xs overflow-auto max-h-[30dvh] sm:max-h-96 select-text leading-relaxed">
              <pre className="m-0 font-mono whitespace-pre-wrap">{texContent}</pre>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
              <div className="text-[11px] font-mono text-charcoal/40 uppercase">
                {texContent.length} characters
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Transform Style Dropdown */}
                <div className="relative inline-block text-left" ref={transformMenuRef}>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setTransformMenuOpen(!transformMenuOpen)}
                    disabled={isTransforming}
                    className="gap-1.5 text-indigo-brand border-indigo-200 bg-indigo-50/60 hover:bg-indigo-100/70"
                    title="Change citation style for all items"
                  >
                    {isTransforming ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Wand2 className="w-3.5 h-3.5" />
                    )}
                    <span>Change Style</span>
                    <ChevronDown className="w-3 h-3 text-indigo-brand/70" />
                  </Button>

                  {transformMenuOpen && (
                    <div className="absolute left-0 sm:left-auto sm:right-0 bottom-full mb-1 z-50 w-56 rounded-xl bg-white border border-border-light shadow-xl py-1 text-xs font-sans text-charcoal-800 animate-in fade-in zoom-in-95 duration-100">
                      <div className="px-3 py-1.5 text-[10px] font-mono text-charcoal/40 uppercase tracking-widest border-b border-border-light/60">
                        Select Target Style
                      </div>
                      <div className="max-h-48 overflow-y-auto py-1">
                        {styles.map((style) => (
                          <button
                            key={style.id}
                            type="button"
                            onClick={() => handleTransform(style.id, style.name)}
                            className="w-full text-left px-3 py-1.5 hover:bg-cream-200 transition-colors flex items-center justify-between text-xs cursor-pointer"
                          >
                            <span className="truncate mr-2">{style.name}</span>
                            {selectedStyleId === style.id && (
                              <Check className="w-3.5 h-3.5 text-indigo-brand shrink-0" />
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

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
