import React, { useState, useEffect } from 'react';
import {
  Plus,
  Trash2,
  Edit2,
  Copy,
  Check,
  Loader2,
  BookOpen,
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
import { VariablesGuide } from '@/components/styles/VariablesGuide';
import { VisualTemplateBuilder } from '@/components/styles/VisualTemplateBuilder';

export const StyleManagerDialog: React.FC = () => {
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector((state) => state.ui.isStyleManagerModalOpen);
  const { styles, selectedStyleId, isLoading } = useAppSelector(
    (state) => state.styles
  );

  const [mode, setMode] = useState<'list' | 'editor' | 'guide'>('list');
  const [previousMode, setPreviousMode] = useState<'list' | 'editor'>('list');
  const [editingStyleId, setEditingStyleId] = useState<string | null>(null);
  const [name, setName] = useState<string>('');
  const [template, setTemplate] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Load styles when modal opens
  useEffect(() => {
    if (isOpen) {
      dispatch(fetchStyles());
      setMode('list');
      setEditingStyleId(null);
      setDeleteConfirmId(null);
    }
  }, [isOpen, dispatch]);

  const isProtectedStyle = (style: CitationStyle) =>
    style.slug === 'iop-default' || style.name.trim().toLowerCase() === 'iop';

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
    if (isProtectedStyle(style)) return;
    setEditingStyleId(style.id);
    setName(style.name);
    setTemplate(style.template);
    setMode('editor');
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
        mode === 'guide'
          ? 'Allowed Variables & Fallback Rules'
          : mode === 'editor'
          ? editingStyleId
            ? 'Edit Citation Style'
            : 'Create New Citation Style'
          : 'Citation Styles Manager'
      }
      description={
        mode === 'guide'
          ? 'Complete reference for author representation variants, bibliographic variables, and fallback rules.'
          : mode === 'editor'
          ? 'Drag variables and text blocks to build your custom citation style.'
          : 'Customize, create, and manage reference bibliography formats.'
      }
      maxWidth={mode === 'guide' || mode === 'editor' ? '4xl' : '3xl'}
    >
      <div className="space-y-4">
        {mode === 'guide' ? (
          <VariablesGuide
            onBack={() => setMode(previousMode)}
            backLabel={previousMode === 'editor' ? 'Back to Style Editor' : 'Back to Styles List'}
            onSelectTag={() => {
              // Informational in visual builder
            }}
          />
        ) : mode === 'list' ? (
          <>
            {/* Action Bar */}
            <div className="flex items-center justify-between pb-2 border-b border-border-light">
              <span className="text-xs font-mono text-charcoal/60 uppercase tracking-wider">
                {styles.length} Available Styles
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPreviousMode('list');
                    setMode('guide');
                  }}
                  className="gap-1.5 text-indigo-brand border-indigo-200 bg-indigo-50/60 hover:bg-indigo-100/70"
                  title="View Allowed Variables & Fallback Rules"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Variables Guide</span>
                  <span className="sm:hidden">Guide</span>
                </Button>

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
                          </div>

                          <div className="p-2 rounded-lg bg-charcoal-900/5 text-charcoal/70 font-mono text-[11px] leading-relaxed break-all border border-charcoal/10 select-all">
                            {style.template}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
                          {isSelected ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-indigo-brand text-white shadow-2xs">
                              <Check className="w-3 h-3" />
                              <span>Active</span>
                            </span>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => dispatch(setSelectedStyleId(style.id))}
                              className="text-charcoal/70 hover:text-indigo-brand"
                            >
                              Select
                            </Button>
                          )}

                          {/* Duplicate Icon Button */}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenCreate(style.template, style.name)}
                            className="p-1.5 text-charcoal/60 hover:text-indigo-brand border-border-light bg-white"
                            title="Duplicate Style"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </Button>

                          {/* Edit Icon Button */}
                          {!isProtectedStyle(style) && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleOpenEdit(style)}
                              className="p-1.5 text-indigo-brand border-indigo-200 bg-indigo-50/40 hover:bg-indigo-100/60"
                              title="Edit Style"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </Button>
                          )}

                          {/* Delete Icon Button */}
                          {!isProtectedStyle(style) && (
                            isConfirmingDelete ? (
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
                            )
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
            onOpenGuide={() => {
              setPreviousMode('editor');
              setMode('guide');
            }}
            onSave={handleSave}
            isSaving={isSaving}
            isEdit={!!editingStyleId}
            isProtected={
              editingStyleId
                ? isProtectedStyle(styles.find((s) => s.id === editingStyleId) || ({} as CitationStyle))
                : false
            }
            onDelete={() => {
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
