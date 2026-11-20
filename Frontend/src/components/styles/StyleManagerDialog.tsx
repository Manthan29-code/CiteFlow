import React, { useState, useEffect } from 'react';
import {
  Plus,
  Trash2,
  Edit2,
  Copy,
  Check,
  Loader2,
  Palette,
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
import { Modal } from '@/components/common/Modal';
import { Button } from '@/components/common/Button';
import { CitationStyle } from '@/types/api';
import { cn } from '@/lib/utils';
import { VisualTemplateBuilder } from '@/components/styles/VisualTemplateBuilder';

export const StyleManagerDialog: React.FC = () => {
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector((state) => state.ui.isStyleManagerModalOpen);
  const { styles, selectedStyleId, isLoading } = useAppSelector(
    (state) => state.styles
  );
  const hasCitations = useAppSelector((state) =>
    Object.values(state.jobs.jobsById).some((j) => j.status === 'succeeded')
  );

  const [mode, setMode] = useState<'list' | 'editor'>('list');
  const [editingStyleId, setEditingStyleId] = useState<string | null>(null);
  const [name, setName] = useState<string>('');
  const [template, setTemplate] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [copiedStyleId, setCopiedStyleId] = useState<string | null>(null);

  // Load styles when modal opens
  useEffect(() => {
    if (isOpen) {
      dispatch(fetchStyles());
      setMode('list');
      setEditingStyleId(null);
      setDeleteConfirmId(null);
    }
  }, [isOpen, dispatch]);

  const handleOpenCreate = (baseTemplate?: string, baseName?: string) => {
    setEditingStyleId(null);
    const initialName = baseName ? `${baseName} (Copy)` : 'My Custom Style';
    setName(initialName);
    const initialTpl =
      baseTemplate ||
      '\\bibitem{citation key} firstname . surname , title , \\textit{ journal }, vol. volume , no. issue , Article article number , year . \\href{doi url}{doi url}';
    setTemplate(initialTpl);
    setMode('editor');
  };

  const handleOpenEdit = (style: CitationStyle) => {
    setEditingStyleId(style.id);
    setName(style.name);
    setTemplate(style.template);
    setMode('editor');
  };

  const handleCopyTemplate = async (templateStr: string, styleId: string, styleName: string) => {
    try {
      const cleanTemplate = templateStr.replace(/^\s*%.*$/gm, '').trim();
      await navigator.clipboard.writeText(cleanTemplate);
      setCopiedStyleId(styleId);
      dispatch(addToast({ type: 'success', message: `Copied "${styleName}" template to clipboard.` }));
      setTimeout(() => {
        setCopiedStyleId((prev) => (prev === styleId ? null : prev));
      }, 2000);
    } catch {
      dispatch(addToast({ type: 'error', message: 'Failed to copy to clipboard.' }));
    }
  };

  const handleClose = () => {
    dispatch(closeStyleManagerModal());
  };

  const handleSave = async () => {
    const resolvedName = name.trim() || 'My Custom Style';

    setIsSaving(true);
    try {
      const finalTemplate = template.trim();

      if (editingStyleId) {
        await dispatch(
          editStyle({
            id: editingStyleId,
            data: { name: resolvedName, template: finalTemplate },
          })
        ).unwrap();
        dispatch(addToast({ type: 'success', message: `Style "${resolvedName}" updated successfully.` }));
      } else {
        await dispatch(
          createNewStyle({ name: resolvedName, template: finalTemplate })
        ).unwrap();
        dispatch(addToast({ type: 'success', message: `Style "${resolvedName}" created and selected.` }));
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
    if (styles.length <= 1 && hasCitations) {
      dispatch(
        addToast({
          type: 'error',
          message: 'You cannot delete your only citation style while you have generated citations.',
        })
      );
      setDeleteConfirmId(null);
      return;
    }
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
      title={
        mode === 'editor'
          ? editingStyleId
            ? 'Edit Citation Style'
            : 'Create New Citation Style'
          : 'Citation Styles Manager'
      }
      description={
        mode === 'editor'
          ? undefined
          : 'Customize, create, and manage reference bibliography formats.'
      }
      maxWidth={mode === 'editor' ? '4xl' : '3xl'}
    >
      <div className="space-y-4">
        {mode === 'list' ? (
          <>
            {/* Action Bar */}
            <div className="flex items-center justify-between pb-2 border-b border-border-light">
              <span className="text-xs font-mono text-charcoal/60 uppercase tracking-wider">
                {styles.length} Available Styles
              </span>
              <div className="flex items-center gap-2">
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
            </div>

            {/* Styles Cards List */}
            <div className="space-y-2.5 max-h-[64vh] overflow-y-auto pr-1 pb-2">
              {isLoading && styles.length === 0 ? (
                <div className="py-12 flex flex-col items-center justify-center text-charcoal/50">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-brand mb-2" />
                  <span className="text-xs font-mono">Loading styles...</span>
                </div>
              ) : styles.length === 0 ? (
                <div className="py-12 px-4 flex flex-col items-center justify-center text-center">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mb-3 text-indigo-brand">
                    <Palette className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-charcoal-900 mb-1">No Citation Styles Available</h3>
                  <p className="text-xs text-charcoal/60 max-w-sm">
                    All citation styles have been removed. You need at least one citation style to generate bibliographies.
                  </p>
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
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-charcoal-900 text-sm truncate">
                              {style.name}
                            </span>
                            {isSelected && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-medium bg-indigo-brand text-white shadow-2xs shrink-0">
                                <Check className="w-3 h-3" />
                                <span>Active</span>
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1.5 shrink-0">
                          {!isSelected && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => dispatch(setSelectedStyleId(style.id))}
                              className="text-charcoal/70 hover:text-indigo-brand"
                            >
                              Select
                            </Button>
                          )}

                          {/* Edit Icon Button */}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenEdit(style)}
                            className="p-1.5 text-indigo-brand border-indigo-200 bg-indigo-50/40 hover:bg-indigo-100/60"
                            title="Edit Style"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </Button>

                          {/* Delete Icon Button */}
                          {isConfirmingDelete ? (
                            <div className="flex items-center gap-1 bg-red-50 p-1 rounded-lg border border-red-200">
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={() => handleDelete(style.id, style.name)}
                                className="bg-red-600 hover:bg-red-700 text-white h-6 px-1.5 text-[11px]"
                              >
                                Confirm
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setDeleteConfirmId(null)}
                                className="h-6 px-1.5 text-[11px]"
                              >
                                Cancel
                              </Button>
                            </div>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setDeleteConfirmId(style.id)}
                              className="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 bg-white"
                              title="Delete Style"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
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
          /* Editor Mode: Visual Template Builder */
          <VisualTemplateBuilder
            initialTemplate={template}
            initialName={name}
            onChangeName={(newName) => setName(newName)}
            onChangeTemplate={(newTpl) => setTemplate(newTpl)}
            onBack={() => setMode('list')}
            onSave={handleSave}
            isSaving={isSaving}
            isEdit={!!editingStyleId}
            isProtected={false}
            onDelete={() => {
              if (styles.length <= 1 && hasCitations) {
                dispatch(
                  addToast({
                    type: 'error',
                    message: 'You cannot delete your only citation style while you have generated citations.',
                  })
                );
                return;
              }
              const s = styles.find((x) => x.id === editingStyleId);
              if (s) {
                handleDelete(s.id, s.name);
                setMode('list');
              }
            }}
          />
        )}
      </div>
    </Modal>
  );
};
