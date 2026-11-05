import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Palette,
  Plus,
  Trash2,
  Edit2,
  Copy,
  Check,
  AlertCircle,
  Eye,
  Sparkles,
  ChevronRight,
  ArrowLeft,
  Loader2,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { closeStyleManagerModal, addToast } from '@/store/slices/uiSlice';
import {
  fetchStyles,
  createNewStyle,
  editStyle,
  removeStyle,
  setSelectedStyleId,
} from '@/store/slices/stylesSlice';
import { validateCitationTemplate } from '@/api/citationStyles';
import { Modal } from '@/components/common/Modal';
import { Button } from '@/components/common/Button';
import { CitationStyle } from '@/types/api';
import { cn } from '@/lib/utils';

export const StyleManagerDialog: React.FC = () => {
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector((state) => state.ui.isStyleManagerModalOpen);
  const { styles, selectedStyleId, allowedFields, isLoading } = useAppSelector(
    (state) => state.styles
  );

  const [mode, setMode] = useState<'list' | 'editor'>('list');
  const [editingStyleId, setEditingStyleId] = useState<string | null>(null);
  const [name, setName] = useState<string>('');
  const [template, setTemplate] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Autocomplete state
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [suggestionQuery, setSuggestionQuery] = useState<string>('');
  const [suggestionCursorStart, setSuggestionCursorStart] = useState<number>(-1);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState<number>(0);

  // Live preview & validation state
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [livePreview, setLivePreview] = useState<string>('');
  const [isValidating, setIsValidating] = useState<boolean>(false);

  // Load styles when modal opens
  useEffect(() => {
    if (isOpen) {
      dispatch(fetchStyles());
      setMode('list');
      setEditingStyleId(null);
      setDeleteConfirmId(null);
    }
  }, [isOpen, dispatch]);

  // Handle autocomplete filtering
  const filteredFields = useMemo(() => {
    if (!suggestionQuery) return allowedFields;
    const q = suggestionQuery.toUpperCase();
    return allowedFields.filter((f) => f.toUpperCase().includes(q));
  }, [allowedFields, suggestionQuery]);

  // Live validation & preview debounce
  useEffect(() => {
    if (mode !== 'editor') return;

    if (!template.trim()) {
      setValidationErrors(['Template cannot be empty.']);
      setLivePreview('');
      return;
    }

    // Local tag syntax check
    const tagMatches = template.match(/<([^>]+)>/g) || [];
    const localErrors: string[] = [];

    if (tagMatches.length === 0) {
      localErrors.push('Template must contain at least one valid <TAG> placeholder.');
    }

    tagMatches.forEach((rawTag) => {
      const cleanTag = rawTag.slice(1, -1).trim();
      if (!allowedFields.includes(cleanTag)) {
        localErrors.push(`Unknown field tag '${rawTag}'.`);
      }
    });

    if (localErrors.length > 0) {
      setValidationErrors(localErrors);
      setLivePreview('');
      return;
    }

    // Remote backend validation & preview
    let isCancelled = false;
    setIsValidating(true);
    const timer = setTimeout(async () => {
      try {
        const res = await validateCitationTemplate(template);
        if (!isCancelled) {
          if (res.valid) {
            setValidationErrors([]);
            setLivePreview(res.preview || '');
          } else {
            setValidationErrors(res.errors);
            setLivePreview('');
          }
        }
      } catch {
        if (!isCancelled) {
          // If network error, still clear errors if local check passed
          setValidationErrors([]);
        }
      } finally {
        if (!isCancelled) setIsValidating(false);
      }
    }, 250);

    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [template, mode, allowedFields]);

  const handleOpenCreate = (baseTemplate?: string, baseName?: string) => {
    setEditingStyleId(null);
    setName(baseName ? `${baseName} (Copy)` : '');
    setTemplate(
      baseTemplate ||
        '\\bibitem{<CITATION_KEY>} <AUTHORS_LAST_FIRST()>. <TITLE>. <JOURNAL_ABBREVIATION> <YEAR>;<VOLUME>(<ISSUE>):<ARTICLE_NUMBER>. doi:<DOI>.'
    );
    setMode('editor');
  };

  const handleOpenEdit = (style: CitationStyle) => {
    if (style.is_builtin) return;
    setEditingStyleId(style.id);
    setName(style.name);
    setTemplate(style.template);
    setMode('editor');
  };

  const handleClose = () => {
    dispatch(closeStyleManagerModal());
  };

  // Textarea input & cursor change for autocomplete
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    const cursorPos = e.target.selectionStart;
    setTemplate(val);

    // Look backwards from cursor to see if inside an unclosed `<`
    const textBeforeCursor = val.slice(0, cursorPos);
    const lastOpenIndex = textBeforeCursor.lastIndexOf('<');
    const lastCloseIndex = textBeforeCursor.lastIndexOf('>');

    if (lastOpenIndex !== -1 && lastOpenIndex > lastCloseIndex) {
      const query = textBeforeCursor.slice(lastOpenIndex + 1);
      setShowSuggestions(true);
      setSuggestionQuery(query);
      setSuggestionCursorStart(lastOpenIndex);
      setActiveSuggestionIndex(0);
    } else {
      setShowSuggestions(false);
    }
  };

  const insertTag = (tag: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    let before = '';
    let after = '';

    if (showSuggestions && suggestionCursorStart !== -1) {
      before = template.slice(0, suggestionCursorStart);
      const afterCursor = template.slice(textarea.selectionEnd);
      // If there is an immediate closing '>', skip it
      after = afterCursor.startsWith('>') ? afterCursor.slice(1) : afterCursor;
    } else {
      const pos = textarea.selectionStart || template.length;
      before = template.slice(0, pos);
      after = template.slice(pos);
    }

    const inserted = `<${tag}>`;
    const newContent = before + inserted + after;
    setTemplate(newContent);
    setShowSuggestions(false);

    // Reposition cursor after inserted tag
    setTimeout(() => {
      textarea.focus();
      const newCursor = before.length + inserted.length;
      textarea.setSelectionRange(newCursor, newCursor);
    }, 0);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!showSuggestions || filteredFields.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveSuggestionIndex((prev) => (prev + 1) % filteredFields.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveSuggestionIndex((prev) => (prev - 1 + filteredFields.length) % filteredFields.length);
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      insertTag(filteredFields[activeSuggestionIndex]);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  const handleSave = async () => {
    if (!name.trim()) {
      dispatch(addToast({ type: 'error', message: 'Style name cannot be empty.' }));
      return;
    }
    if (validationErrors.length > 0) {
      dispatch(addToast({ type: 'error', message: 'Please fix template errors before saving.' }));
      return;
    }

    setIsSaving(true);
    try {
      if (editingStyleId) {
        await dispatch(editStyle({ id: editingStyleId, data: { name: name.trim(), template: template.trim() } })).unwrap();
        dispatch(addToast({ type: 'success', message: `Style "${name}" updated successfully.` }));
      } else {
        const created = await dispatch(createNewStyle({ name: name.trim(), template: template.trim() })).unwrap();
        dispatch(addToast({ type: 'success', message: `Style "${name}" created and selected.` }));
      }
      setMode('list');
      setEditingStyleId(null);
    } catch (err: unknown) {
      dispatch(addToast({ type: 'error', message: String(err) }));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (styleId: string, styleName: string) => {
    try {
      await dispatch(removeStyle(styleId)).unwrap();
      dispatch(addToast({ type: 'success', message: `Style "${styleName}" deleted.` }));
      setDeleteConfirmId(null);
    } catch (err: unknown) {
      dispatch(addToast({ type: 'error', message: String(err) }));
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={mode === 'editor' ? (editingStyleId ? 'Edit Citation Style' : 'Create New Citation Style') : 'Citation Styles Manager'}
      description={
        mode === 'editor'
          ? 'Define your LaTeX \\bibitem template using uppercase <TAG> placeholders.'
          : 'Customize, create, and manage reference bibliography formats.'
      }
      maxWidth="3xl"
    >
      <div className="space-y-4">
        {mode === 'list' ? (
          <>
            {/* Action Bar */}
            <div className="flex items-center justify-between pb-2 border-b border-border-light">
              <span className="text-xs font-mono text-charcoal/60 uppercase tracking-wider">
                {styles.length} Available Styles
              </span>
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleOpenCreate()}
                className="gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New Style</span>
              </Button>
            </div>

            {/* Styles Cards List */}
            <div className="space-y-2.5 max-h-[50vh] overflow-y-auto pr-1">
              {isLoading && styles.length === 0 ? (
                <div className="py-12 flex flex-col items-center justify-center text-charcoal/50">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-brand mb-2" />
                  <span className="text-xs font-mono">Loading styles...</span>
                </div>
              ) : (
                styles.map((style) => {
                  const isSelected = selectedStyleId === style.id;
                  const isConfirmingDelete = deleteConfirmId === style.id;

                  return (
                    <div
                      key={style.id}
                      className={cn(
                        'p-3.5 rounded-xl border transition-all text-xs',
                        isSelected
                          ? 'border-indigo-brand/40 bg-indigo-50/40 shadow-xs'
                          : 'border-border-light bg-white hover:border-border-light/80'
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-charcoal-900 text-sm truncate">
                              {style.name}
                            </span>
                            {style.is_builtin ? (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-cream-200 text-charcoal/60 border border-border-light">
                                Built-in
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                                Custom
                              </span>
                            )}
                            {isSelected && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-brand text-white">
                                Active Default
                              </span>
                            )}
                          </div>
                          <p className="font-mono text-[11px] text-charcoal/60 line-clamp-2 bg-cream-100 p-2 rounded-lg border border-border-light/60 mt-1 select-all">
                            {style.template}
                          </p>
                        </div>

                        {/* Style Actions */}
                        <div className="flex items-center gap-1 shrink-0 pt-0.5">
                          <button
                            type="button"
                            onClick={() => dispatch(setSelectedStyleId(style.id))}
                            title="Set as active generation style"
                            className={cn(
                              'px-2 py-1 rounded-lg text-xs font-mono font-medium transition-colors cursor-pointer',
                              isSelected
                                ? 'bg-indigo-brand text-white'
                                : 'text-charcoal/60 hover:text-indigo-brand hover:bg-cream-200'
                            )}
                          >
                            {isSelected ? 'Active' : 'Select'}
                          </button>

                          <button
                            type="button"
                            onClick={() => handleOpenCreate(style.template, style.name)}
                            title="Duplicate this style template"
                            className="p-1.5 rounded-lg text-charcoal/40 hover:text-charcoal hover:bg-cream-200 transition-colors"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>

                          {!style.is_builtin && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleOpenEdit(style)}
                                title="Edit this style"
                                className="p-1.5 rounded-lg text-charcoal/40 hover:text-indigo-brand hover:bg-cream-200 transition-colors"
                              >
                                <Edit2 className="w-3.5 h-3.5" />
                              </button>

                              {isConfirmingDelete ? (
                                <div className="flex items-center gap-1 bg-red-50 p-1 rounded-lg border border-red-200 animate-in fade-in duration-150">
                                  <button
                                    type="button"
                                    onClick={() => handleDelete(style.id, style.name)}
                                    className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-red-600 text-white hover:bg-red-700"
                                  >
                                    Confirm
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setDeleteConfirmId(null)}
                                    className="px-1.5 py-0.5 rounded text-[10px] font-mono text-charcoal/60 hover:text-charcoal"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => setDeleteConfirmId(style.id)}
                                  title="Delete custom style"
                                  className="p-1.5 rounded-lg text-charcoal/40 hover:text-red-600 hover:bg-red-50 transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </>
        ) : (
          /* Editor Mode */
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setMode('list')}
                className="flex items-center gap-1.5 text-xs font-mono text-charcoal/60 hover:text-indigo-brand transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Styles List</span>
              </button>
              <span className="text-[11px] font-mono text-charcoal/40">
                Type <kbd className="px-1 py-0.5 rounded bg-cream-200 border border-border-light text-charcoal-900">&lt;</kbd> inside template for autocomplete
              </span>
            </div>

            {/* Style Name Input */}
            <div>
              <label htmlFor="style-name-input" className="block text-xs font-mono uppercase tracking-wider text-charcoal/70 mb-1">
                Style Name <span className="text-red-500">*</span>
              </label>
              <input
                id="style-name-input"
                type="text"
                placeholder="e.g. My Custom Journal Style"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 text-xs font-sans bg-white border border-border-light rounded-xl text-charcoal-900 placeholder:text-charcoal/30 focus:outline-none focus:ring-2 focus:ring-indigo-brand"
              />
            </div>

            {/* Quick Tag Pills Helper */}
            <div>
              <div className="text-[11px] font-mono text-charcoal/50 uppercase tracking-wider mb-1.5">
                Quick Insert Variables:
              </div>
              <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto p-1.5 bg-cream-100 rounded-xl border border-border-light">
                {allowedFields.map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => insertTag(f)}
                    className="px-2 py-0.5 rounded-lg text-[10px] font-mono bg-white hover:bg-indigo-50 hover:text-indigo-brand hover:border-indigo-200 text-charcoal-800 border border-border-light transition-colors shadow-2xs cursor-pointer"
                  >
                    &lt;{f}&gt;
                  </button>
                ))}
              </div>
            </div>

            {/* Template Textarea with Autocomplete */}
            <div className="relative">
              <label htmlFor="style-template-input" className="block text-xs font-mono uppercase tracking-wider text-charcoal/70 mb-1">
                LaTeX Template String <span className="text-red-500">*</span>
              </label>
              <textarea
                ref={textareaRef}
                id="style-template-input"
                rows={4}
                value={template}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                placeholder="e.g. \bibitem{<CITATION_KEY>} <AUTHORS_LAST_FIRST()>. <TITLE>. <JOURNAL_ABBREVIATION> <YEAR>;<VOLUME>(<ISSUE>):<ARTICLE_NUMBER>. doi:<DOI>."
                className="w-full px-3 py-2 text-xs font-mono bg-white border border-border-light rounded-xl text-charcoal-900 placeholder:text-charcoal/30 focus:outline-none focus:ring-2 focus:ring-indigo-brand leading-relaxed"
              />

              {/* Autocomplete Dropdown Popup */}
              <AnimatePresence>
                {showSuggestions && (
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 5 }}
                    className="absolute z-50 left-2 right-2 bottom-full mb-1 max-h-48 overflow-y-auto rounded-xl bg-charcoal-900 text-cream border border-charcoal-700 shadow-xl py-1"
                  >
                    <div className="px-3 py-1 text-[10px] font-mono text-cream/40 uppercase tracking-widest border-b border-charcoal-800">
                      Suggested Fields ({filteredFields.length})
                    </div>
                    {filteredFields.length === 0 ? (
                      <div className="px-3 py-2 text-xs text-cream/50 font-mono">
                        No matching field tags.
                      </div>
                    ) : (
                      filteredFields.map((field, idx) => (
                        <button
                          key={field}
                          type="button"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            insertTag(field);
                          }}
                          className={cn(
                            'w-full text-left px-3 py-1.5 text-xs font-mono transition-colors flex items-center justify-between',
                            idx === activeSuggestionIndex
                              ? 'bg-indigo-600 text-white'
                              : 'text-cream/80 hover:bg-charcoal-800 hover:text-white'
                          )}
                        >
                          <span>&lt;{field}&gt;</span>
                          <span className="text-[10px] opacity-60">Tab / Enter</span>
                        </button>
                      ))
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Validation Errors Box */}
            {validationErrors.length > 0 && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-sans space-y-1">
                <div className="flex items-center gap-1.5 font-semibold text-red-800">
                  <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                  <span>Template Syntax Warning</span>
                </div>
                <ul className="list-disc list-inside space-y-0.5 text-[11px] font-mono">
                  {validationErrors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Live LaTeX Citation Preview Box */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-mono text-charcoal/60 uppercase tracking-wider flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-indigo-brand" />
                  <span>Live Preview (Ghosh 2017 Sample)</span>
                </span>
                {isValidating && (
                  <span className="text-[10px] font-mono text-indigo-brand animate-pulse">
                    Updating preview...
                  </span>
                )}
              </div>
              <div className="rounded-xl border border-charcoal-800 bg-charcoal-900 text-cream p-3 font-mono text-xs overflow-auto max-h-32 select-all leading-relaxed shadow-inner">
                {livePreview ? (
                  <pre className="m-0 whitespace-pre-wrap">{livePreview}</pre>
                ) : (
                  <span className="text-charcoal/50 italic font-sans text-xs">
                    {validationErrors.length > 0
                      ? 'Fix template syntax above to preview citation output.'
                      : 'Rendering preview...'}
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-light">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMode('list')}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSave}
                disabled={isSaving || validationErrors.length > 0 || !name.trim()}
                className="gap-1.5"
              >
                {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                <span>{editingStyleId ? 'Save Changes' : 'Create Style'}</span>
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

