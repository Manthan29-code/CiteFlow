import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GripVertical,
  Plus,
  Trash2,
  Check,
  Undo2,
  Redo2,
  Maximize2,
  Minimize2,
  Copy,
  Eye,
  Loader2,
  AlertCircle,
  BookOpen,
  ArrowLeft,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/common/Button';
import { validateCitationTemplate } from '@/api/citationStyles';
import { cn } from '@/lib/utils';

export type BlockType = 'variable' | 'text';

export interface BuilderBlock {
  id: string;
  type: BlockType;
  text?: string;
  variable?: string;
  included?: boolean;
  isBold?: boolean;
  isLink?: boolean;
}

export interface VariableDef {
  id: string;
  label: string;
  category: 'author' | 'publication' | 'identification';
  supportsBold?: boolean;
  supportsLink?: boolean;
}

export const AVAILABLE_VARIABLES: VariableDef[] = [
  // Author metadata
  { id: 'surname', label: 'surname', category: 'author' },
  { id: 'firstname', label: 'firstname', category: 'author' },
  { id: 'middle name', label: 'middle name', category: 'author' },

  // Publication metadata
  { id: 'title', label: 'title', category: 'publication' },
  { id: 'journal', label: 'journal', category: 'publication' },
  { id: 'journal abbr', label: 'journal abbr', category: 'publication' },
  { id: 'volume', label: 'volume', category: 'publication', supportsBold: true },
  { id: 'issue', label: 'issue', category: 'publication', supportsBold: true },
  { id: 'article number', label: 'article number', category: 'publication', supportsBold: true },
  { id: 'first page', label: 'first page', category: 'publication' },
  { id: 'year', label: 'year', category: 'publication' },

  // Identification metadata
  { id: 'citation key', label: 'citation key', category: 'identification' },
  { id: 'doi url', label: 'doi url', category: 'identification', supportsLink: true },
  { id: 'doi', label: 'doi', category: 'identification', supportsLink: true },
];

export const DEFAULT_INITIAL_BLOCKS: BuilderBlock[] = [
  { id: 'b_1', type: 'text', text: '\\bibitem{' },
  { id: 'b_2', type: 'variable', variable: 'citation key', included: true },
  { id: 'b_3', type: 'text', text: '} ' },
  { id: 'b_4', type: 'variable', variable: 'firstname', included: true },
  { id: 'b_5', type: 'text', text: ' . ' },
  { id: 'b_6', type: 'variable', variable: 'surname', included: true },
  { id: 'b_7', type: 'text', text: ', ' },
  { id: 'b_8', type: 'variable', variable: 'title', included: true },
  { id: 'b_9', type: 'text', text: ', \\textit{' },
  { id: 'b_10', type: 'variable', variable: 'journal', included: true },
  { id: 'b_11', type: 'text', text: '}, vol. ' },
  { id: 'b_12', type: 'variable', variable: 'volume', included: true, isBold: false },
  { id: 'b_13', type: 'text', text: ', no. ' },
  { id: 'b_14', type: 'variable', variable: 'issue', included: true, isBold: false },
  { id: 'b_15', type: 'text', text: ', Article ' },
  { id: 'b_16', type: 'variable', variable: 'article number', included: true, isBold: false },
  { id: 'b_17', type: 'text', text: ', ' },
  { id: 'b_18', type: 'variable', variable: 'year', included: true },
  { id: 'b_19', type: 'text', text: '. ' },
  { id: 'b_20', type: 'variable', variable: 'doi url', included: true, isLink: true },
];

/**
 * Converts visual blocks into a LaTeX template string with optional embedded state comment.
 */
export function serializeBlocksToTemplate(
  blocks: BuilderBlock[],
  truncateAuthors: boolean,
  andBeforeLast: boolean,
  includeStateComment: boolean = true
): string {
  let templateBody = '';

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    if (block.type === 'text') {
      templateBody += block.text ?? ' ';
    } else if (block.type === 'variable') {
      if (block.included === false) continue;
      const v = (block.variable || '').trim();

      // Ensure space between consecutive variables so they never fuse
      if (
        i > 0 &&
        blocks[i - 1].type === 'variable' &&
        blocks[i - 1].included !== false &&
        !templateBody.endsWith(' ')
      ) {
        templateBody += ' ';
      }

      if (block.isBold && ['volume', 'issue', 'article number'].includes(v)) {
        templateBody += `\\textbf{${v}}`;
      } else if (block.isLink && (v === 'doi url' || v === 'doi')) {
        templateBody += `\\href{doi url}{${v}}`;
      } else {
        templateBody += v;
      }
    }
  }

  const directives: string[] = [];
  if (!truncateAuthors) {
    directives.push('% truncate_authors: false');
  }
  if (andBeforeLast) {
    directives.push('% and_before_last: true');
  }

  if (includeStateComment) {
    const cleanBlocks = blocks.map((b) => ({
      id: b.id,
      type: b.type,
      text: b.text,
      variable: b.variable,
      included: b.included !== false,
      isBold: !!b.isBold,
      isLink: !!b.isLink,
    }));

    const stateJson = JSON.stringify({
      blocks: cleanBlocks,
      truncateAuthors,
      andBeforeLast,
    });
    directives.push(`% builder_state: ${stateJson}`);
  }

  return directives.length > 0
    ? `${templateBody.trim()}\n${directives.join('\n')}`
    : templateBody.trim();
}

/**
 * Parses an existing template string into builder blocks and flags.
 */
export function deserializeTemplateToBlocks(rawTemplate: string): {
  blocks: BuilderBlock[];
  truncateAuthors: boolean;
  andBeforeLast: boolean;
} {
  if (!rawTemplate || !rawTemplate.trim()) {
    return {
      blocks: [...DEFAULT_INITIAL_BLOCKS],
      truncateAuthors: true,
      andBeforeLast: false,
    };
  }

  // 1. Check for stored builder state
  const stateMatch = rawTemplate.match(/%\s*builder_state:\s*(\{.*\})/);
  if (stateMatch) {
    try {
      const parsed = JSON.parse(stateMatch[1]);
      if (Array.isArray(parsed.blocks) && parsed.blocks.length > 0) {
        return {
          blocks: parsed.blocks,
          truncateAuthors: parsed.truncateAuthors !== false,
          andBeforeLast: !!parsed.andBeforeLast,
        };
      }
    } catch {
      // Fall through to manual parsing
    }
  }

  const truncateAuthors = !rawTemplate.includes('% truncate_authors: false');
  const andBeforeLast = rawTemplate.includes('% and_before_last: true');

  // Strip comment lines
  const cleanTemplate = rawTemplate.replace(/^\s*%.*\n?/gm, '').trim();

  // 2. Tokenize template into text and variable blocks
  const knownKeywords = [
    'authors last first .',
    'authors last first.',
    'authors last first',
    'authors first. last',
    'authors first last',
    'authors',
    'citation key',
    'key',
    'firstname',
    'first name',
    'surname',
    'middle name',
    'title',
    'journal abbreviation',
    'journal abbr',
    'journal',
    'article number',
    'first page',
    'locator',
    'doi url',
    'doi',
    'year',
    'volume',
    'issue',
  ];

  const regex = new RegExp(
    `(\\\\textbf\\{(?:volume|issue|article number)\\})|(\\\\href\\{doi url\\}\\{(?:doi url|doi)\\})|(${knownKeywords
      .map((k) => k.replace('.', '\\.'))
      .join('|')})`,
    'gi'
  );

  const blocks: BuilderBlock[] = [];
  let lastIndex = 0;
  let blockCounter = 1;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(cleanTemplate)) !== null) {
    const textBefore = cleanTemplate.slice(lastIndex, match.index);
    if (textBefore) {
      blocks.push({
        id: `tb_${blockCounter++}`,
        type: 'text',
        text: textBefore,
      });
    }

    const matchedStr = match[0];
    const boldMatch = matchedStr.match(/^\\textbf\{([^}]+)\}$/i);
    const hrefMatch = matchedStr.match(/^\\href\{doi\s+url\}\{(doi\s+url|doi)\}$/i);

    if (boldMatch) {
      const v = boldMatch[1].toLowerCase().trim();
      blocks.push({
        id: `vb_${blockCounter++}`,
        type: 'variable',
        variable: v,
        included: true,
        isBold: true,
      });
    } else if (hrefMatch) {
      const v = hrefMatch[1].toLowerCase().trim();
      blocks.push({
        id: `vb_${blockCounter++}`,
        type: 'variable',
        variable: v,
        included: true,
        isBold: false,
        isLink: true,
      });
    } else {
      const lower = matchedStr.toLowerCase().trim();
      let canonicalVar = lower;
      if (lower === 'key') canonicalVar = 'citation key';
      if (lower === 'first name') canonicalVar = 'firstname';
      if (lower === 'journal abbreviation') canonicalVar = 'journal abbr';

      blocks.push({
        id: `vb_${blockCounter++}`,
        type: 'variable',
        variable: canonicalVar,
        included: true,
        isBold: false,
        isLink: false,
      });
    }

    lastIndex = regex.lastIndex;
  }

  const trailing = cleanTemplate.slice(lastIndex);
  if (trailing) {
    blocks.push({
      id: `tb_${blockCounter++}`,
      type: 'text',
      text: trailing,
    });
  }

  return {
    blocks: blocks.length > 0 ? blocks : [...DEFAULT_INITIAL_BLOCKS],
    truncateAuthors,
    andBeforeLast,
  };
}

interface VisualTemplateBuilderProps {
  initialTemplate: string;
  initialName: string;
  onChangeName: (name: string) => void;
  onChangeTemplate: (template: string) => void;
  onBack: () => void;
  onOpenGuide: () => void;
  onSave: () => void;
  isSaving: boolean;
  isEdit: boolean;
  onDelete?: () => void;
  isProtected?: boolean;
}

export const VisualTemplateBuilder: React.FC<VisualTemplateBuilderProps> = ({
  initialTemplate,
  initialName,
  onChangeName,
  onChangeTemplate,
  onBack,
  onOpenGuide,
  onSave,
  isSaving,
  isEdit,
  onDelete,
  isProtected = false,
}) => {
  const parsed = useMemo(() => deserializeTemplateToBlocks(initialTemplate), [initialTemplate]);

  const [name, setName] = useState<string>(initialName || 'My Custom Style');
  const [blocks, setBlocks] = useState<BuilderBlock[]>(parsed.blocks);
  const [truncateAuthors, setTruncateAuthors] = useState<boolean>(parsed.truncateAuthors);
  const [andBeforeLast, setAndBeforeLast] = useState<boolean>(parsed.andBeforeLast);

  // Undo / Redo history
  const [history, setHistory] = useState<BuilderBlock[][]>([parsed.blocks]);
  const [historyIndex, setHistoryIndex] = useState<number>(0);

  // UI States
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);
  const [copiedPreview, setCopiedPreview] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Drag and Drop
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);

  // Live preview & validation
  const [livePreview, setLivePreview] = useState<string>('');
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isValidating, setIsValidating] = useState<boolean>(false);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  // Push new state to history
  const recordHistory = useCallback(
    (newBlocks: BuilderBlock[]) => {
      setHistory((prev) => {
        const sliced = prev.slice(0, historyIndex + 1);
        return [...sliced, newBlocks];
      });
      setHistoryIndex((prev) => prev + 1);
    },
    [historyIndex]
  );

  const handleUndo = () => {
    if (historyIndex > 0) {
      const prevIdx = historyIndex - 1;
      setHistoryIndex(prevIdx);
      setBlocks(history[prevIdx]);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const nextIdx = historyIndex + 1;
      setHistoryIndex(nextIdx);
      setBlocks(history[nextIdx]);
    }
  };

  // Synchronize serialized template back to parent
  useEffect(() => {
    const serialized = serializeBlocksToTemplate(blocks, truncateAuthors, andBeforeLast, true);
    onChangeTemplate(serialized);
  }, [blocks, truncateAuthors, andBeforeLast, onChangeTemplate]);

  // Live preview evaluation (sends clean template without state comments)
  useEffect(() => {
    const previewTpl = serializeBlocksToTemplate(blocks, truncateAuthors, andBeforeLast, false);
    let isCancelled = false;
    setIsValidating(true);

    const timer = setTimeout(async () => {
      try {
        const res = await validateCitationTemplate(previewTpl);
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
          setValidationErrors([]);
        }
      } finally {
        if (!isCancelled) setIsValidating(false);
      }
    }, 200);

    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [blocks, truncateAuthors, andBeforeLast]);

  // Clean preview text wrapped in compilable thebibliography block
  const displayPreview = useMemo(() => {
    if (!livePreview) return '';
    // Strip comment lines
    const cleanLines = livePreview
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith('%'));

    if (cleanLines.length === 0) return '';
    const cleanText = cleanLines.join('\n');

    // If already wrapped in thebibliography, return cleanText
    if (cleanText.includes('\\begin{thebibliography}')) {
      return cleanText;
    }

    // Wrap in standard \begin{thebibliography}{99} ... \end{thebibliography}
    return `\\begin{thebibliography}{99}\n${cleanText}\n\\end{thebibliography}`;
  }, [livePreview]);

  // Helper to count occurrences of variables
  const variableCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const b of blocks) {
      if (b.type === 'variable' && b.variable) {
        counts[b.variable] = (counts[b.variable] || 0) + 1;
      }
    }
    return counts;
  }, [blocks]);

  // Insert Variable action
  const handleInsertVariable = (varDef: VariableDef) => {
    const count = variableCounts[varDef.id] || 0;
    if (count >= 1) return;

    const newBlock: BuilderBlock = {
      id: `vb_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      type: 'variable',
      variable: varDef.id,
      included: true,
      isBold: false,
      isLink: varDef.supportsLink || false,
    };

    const next = [...blocks, newBlock];
    setBlocks(next);
    recordHistory(next);
    setIsDropdownOpen(false);
  };

  // Add free-text block
  const handleAddTextBlock = () => {
    const newBlock: BuilderBlock = {
      id: `tb_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      type: 'text',
      text: ', ',
    };
    const next = [...blocks, newBlock];
    setBlocks(next);
    recordHistory(next);
  };

  // Update text of a text block
  const handleTextChange = (id: string, text: string) => {
    setBlocks((prev) =>
      prev.map((b) => (b.id === id ? { ...b, text } : b))
    );
  };

  // On blur text field, commit to history
  const handleTextBlur = () => {
    recordHistory(blocks);
  };

  // Delete block
  const handleDeleteBlock = (id: string) => {
    const next = blocks.filter((b) => b.id !== id);
    setBlocks(next);
    recordHistory(next);
  };

  // Toggle included
  const handleToggleIncluded = (id: string) => {
    const next = blocks.map((b) =>
      b.id === id ? { ...b, included: b.included === false ? true : false } : b
    );
    setBlocks(next);
    recordHistory(next);
  };

  // Toggle bold
  const handleToggleBold = (id: string) => {
    const next = blocks.map((b) =>
      b.id === id ? { ...b, isBold: !b.isBold } : b
    );
    setBlocks(next);
    recordHistory(next);
  };

  // Toggle link
  const handleToggleLink = (id: string) => {
    const next = blocks.map((b) =>
      b.id === id ? { ...b, isLink: !b.isLink } : b
    );
    setBlocks(next);
    recordHistory(next);
  };

  // Drag and Drop handlers
  const handleDragStart = (e: React.DragEvent, index: number) => {
    e.dataTransfer.setData('text/plain', String(index));
    e.dataTransfer.effectAllowed = 'move';
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dropTargetIndex !== index) {
      setDropTargetIndex(index);
    }
  };

  const handleDrop = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === targetIndex) {
      setDraggedIndex(null);
      setDropTargetIndex(null);
      return;
    }

    const next = [...blocks];
    const [moved] = next.splice(draggedIndex, 1);
    next.splice(targetIndex, 0, moved);

    setBlocks(next);
    recordHistory(next);
    setDraggedIndex(null);
    setDropTargetIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDropTargetIndex(null);
  };

  const handleCopyPreview = () => {
    if (!displayPreview) return;
    navigator.clipboard.writeText(displayPreview);
    setCopiedPreview(true);
    setTimeout(() => setCopiedPreview(false), 1800);
  };

  const handleSaveClick = () => {
    const resolvedName = name.trim() || 'My Custom Style';
    if (!name.trim()) {
      setName(resolvedName);
      onChangeName(resolvedName);
    }
    onSave();
  };

  return (
    <div
      className={cn(
        'space-y-3.5 transition-all',
        isFullscreen
          ? 'fixed inset-0 z-50 bg-[#fcfbf9] p-6 overflow-y-auto max-w-none'
          : 'relative'
      )}
    >
      {/* Top Navigation & Header */}
      <div className="flex items-center justify-between pb-1">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs font-mono text-charcoal/70 hover:text-indigo-brand transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Styles List</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenGuide}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono text-indigo-brand bg-indigo-50/80 border border-indigo-200 hover:bg-indigo-100 transition-colors cursor-pointer"
            title="View Variables & Rules Guide"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Variables Guide</span>
          </button>
          <span className="text-[11px] font-mono text-charcoal/40 hidden sm:inline">
            Type variable name for autocomplete
          </span>
        </div>
      </div>

      {/* Style Name Input Card */}
      <div className="p-3 rounded-xl bg-white border border-border-light shadow-2xs">
        <label
          htmlFor="builder-style-name"
          className="block text-xs font-mono uppercase tracking-wider text-charcoal/70 mb-1 font-medium"
        >
          STYLE NAME <span className="text-red-500">*</span>
        </label>
        <input
          id="builder-style-name"
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            onChangeName(e.target.value);
          }}
          placeholder="e.g. My Custom Journal Style"
          className="w-full px-3 py-1.5 text-xs font-sans bg-slate-50/60 border border-border-light rounded-lg text-charcoal-900 placeholder:text-charcoal/30 focus:outline-none focus:ring-2 focus:ring-indigo-brand"
        />
      </div>

      {/* Workspace Header Toolbar */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-mono uppercase tracking-wider text-charcoal/80 font-medium">
            CITATION TEMPLATE BUILDER <span className="text-red-500">*</span>
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Insert Variable Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsDropdownOpen((prev) => !prev)}
              className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 transition-colors cursor-pointer shadow-2xs"
            >
              <Plus className="w-3.5 h-3.5 text-indigo-600" />
              <span>Insert Variable</span>
              <ChevronDown className="w-3 h-3 text-indigo-500" />
            </button>

            <AnimatePresence>
              {isDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.98 }}
                  className="absolute right-0 top-full mt-1.5 z-50 w-72 max-h-80 overflow-y-auto rounded-xl bg-white border border-border-light shadow-xl p-1 text-xs"
                >
                  {/* Category: Author Metadata */}
                  <div className="px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider text-charcoal/50 bg-slate-50/70 rounded-md">
                    Author Metadata
                  </div>
                  {AVAILABLE_VARIABLES.filter((v) => v.category === 'author').map((v) => {
                    const count = variableCounts[v.id] || 0;
                    const isDisabled = count >= 1;
                    return (
                      <button
                        key={v.id}
                        type="button"
                        disabled={isDisabled}
                        onClick={() => handleInsertVariable(v)}
                        className={cn(
                          'w-full text-left px-2.5 py-1.5 rounded-lg flex items-center justify-between font-mono text-xs transition-colors',
                          isDisabled
                            ? 'opacity-40 cursor-not-allowed text-charcoal/40'
                            : 'hover:bg-indigo-50 hover:text-indigo-900 cursor-pointer text-charcoal-900'
                        )}
                      >
                        <span>{v.label}</span>
                        {isDisabled && <span className="text-[10px] text-charcoal/40 font-sans">Added</span>}
                      </button>
                    );
                  })}

                  {/* Category: Publication Metadata */}
                  <div className="px-2.5 py-1 mt-1 text-[10px] font-mono uppercase tracking-wider text-charcoal/50 bg-slate-50/70 rounded-md">
                    Publication Metadata
                  </div>
                  {AVAILABLE_VARIABLES.filter((v) => v.category === 'publication').map((v) => {
                    const count = variableCounts[v.id] || 0;
                    const isDisabled = count >= 1;
                    return (
                      <button
                        key={v.id}
                        type="button"
                        disabled={isDisabled}
                        onClick={() => handleInsertVariable(v)}
                        className={cn(
                          'w-full text-left px-2.5 py-1.5 rounded-lg flex items-center justify-between font-mono text-xs transition-colors',
                          isDisabled
                            ? 'opacity-40 cursor-not-allowed text-charcoal/40'
                            : 'hover:bg-indigo-50 hover:text-indigo-900 cursor-pointer text-charcoal-900'
                        )}
                      >
                        <span>{v.label}</span>
                        {isDisabled && <span className="text-[10px] text-charcoal/40 font-sans">Added</span>}
                      </button>
                    );
                  })}

                  {/* Category: Identification Metadata */}
                  <div className="px-2.5 py-1 mt-1 text-[10px] font-mono uppercase tracking-wider text-charcoal/50 bg-slate-50/70 rounded-md">
                    Identification Metadata
                  </div>
                  {AVAILABLE_VARIABLES.filter((v) => v.category === 'identification').map((v) => {
                    const count = variableCounts[v.id] || 0;
                    const isDisabled = count >= 1;
                    return (
                      <button
                        key={v.id}
                        type="button"
                        disabled={isDisabled}
                        onClick={() => handleInsertVariable(v)}
                        className={cn(
                          'w-full text-left px-2.5 py-1.5 rounded-lg flex items-center justify-between font-mono text-xs transition-colors',
                          isDisabled
                            ? 'opacity-40 cursor-not-allowed text-charcoal/40'
                            : 'hover:bg-indigo-50 hover:text-indigo-900 cursor-pointer text-charcoal-900'
                        )}
                      >
                        <span>{v.label}</span>
                        {isDisabled && <span className="text-[10px] text-charcoal/40 font-sans">Added</span>}
                      </button>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Quick Add Text Button */}
          <button
            type="button"
            onClick={handleAddTextBlock}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono text-charcoal/70 bg-white border border-border-light hover:bg-slate-50 hover:text-charcoal-900 transition-colors cursor-pointer shadow-2xs"
            title="Add arbitrary text or punctuation"
          >
            <Plus className="w-3 h-3" />
            <span>Text</span>
          </button>

          {/* Undo Button */}
          <button
            type="button"
            onClick={handleUndo}
            disabled={historyIndex <= 0}
            className="p-1 rounded-lg text-charcoal/60 hover:text-charcoal-900 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-100 transition-colors cursor-pointer"
            title="Undo"
          >
            <Undo2 className="w-3.5 h-3.5" />
          </button>

          {/* Redo Button */}
          <button
            type="button"
            onClick={handleRedo}
            disabled={historyIndex >= history.length - 1}
            className="p-1 rounded-lg text-charcoal/60 hover:text-charcoal-900 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-100 transition-colors cursor-pointer"
            title="Redo"
          >
            <Redo2 className="w-3.5 h-3.5" />
          </button>

          {/* Fullscreen Toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen((prev) => !prev)}
            className="p-1 rounded-lg text-charcoal/60 hover:text-charcoal-900 hover:bg-slate-100 transition-colors cursor-pointer"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Main Draggable Workspace Container (Internal scrolling if many blocks) */}
      <div className="rounded-2xl border border-border-light bg-slate-50/50 p-3.5 max-h-48 overflow-y-auto shadow-2xs">
        <div className="flex flex-wrap items-center gap-1.5">
          {blocks.map((block, index) => {
            const isTarget = dropTargetIndex === index;
            const isDragging = draggedIndex === index;

            return (
              <React.Fragment key={block.id}>
                {/* Visual Insertion Line Indicator */}
                {isTarget && (
                  <div className="w-1 h-7 bg-indigo-600 rounded-full animate-pulse mx-0.5 shadow-xs" />
                )}

                <div
                  draggable
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDrop={(e) => handleDrop(e, index)}
                  onDragEnd={handleDragEnd}
                  className={cn(
                    'group relative flex items-center transition-all select-none',
                    isDragging ? 'opacity-30 scale-95' : 'opacity-100'
                  )}
                >
                  {block.type === 'variable' ? (
                    /* Variable Block */
                    <div
                      className={cn(
                        'flex items-center gap-1 px-2 py-1 rounded-xl text-xs font-mono transition-all border shadow-2xs',
                        block.included === false
                          ? 'bg-slate-100 text-charcoal/40 border-slate-200 line-through'
                          : 'bg-emerald-50/90 text-emerald-900 border-emerald-200/90 hover:border-emerald-300'
                      )}
                    >
                      {/* Drag Handle */}
                      <GripVertical className="w-3 h-3 text-emerald-400 cursor-grab active:cursor-grabbing shrink-0" />

                      {/* Variable Name */}
                      <span className="font-semibold">{block.variable}</span>

                      {/* Inclusion Checkbox */}
                      <button
                        type="button"
                        onClick={() => handleToggleIncluded(block.id)}
                        className={cn(
                          'w-4 h-4 rounded flex items-center justify-center transition-colors cursor-pointer ml-0.5',
                          block.included !== false
                            ? 'bg-indigo-600 text-white'
                            : 'border border-slate-300 bg-white text-transparent'
                        )}
                        title={block.included !== false ? 'Included in citation' : 'Excluded from citation'}
                      >
                        <Check className="w-3 h-3 stroke-[3]" />
                      </button>

                      {/* Bold Option for volume, issue, article number */}
                      {['volume', 'issue', 'article number'].includes(block.variable || '') && (
                        <label className="flex items-center gap-1 ml-1 text-[11px] font-sans text-charcoal/70 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={!!block.isBold}
                            onChange={() => handleToggleBold(block.id)}
                            className="w-3.5 h-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                          />
                          <span>Bold</span>
                        </label>
                      )}

                      {/* Link Option for doi, doi url */}
                      {['doi', 'doi url'].includes(block.variable || '') && (
                        <label className="flex items-center gap-1 ml-1 text-[11px] font-sans text-indigo-900 font-medium cursor-pointer">
                          <input
                            type="checkbox"
                            checked={!!block.isLink}
                            onChange={() => handleToggleLink(block.id)}
                            className="w-3.5 h-3.5 rounded border-indigo-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                          />
                          <span>Link</span>
                        </label>
                      )}

                      {/* Remove Button */}
                      <button
                        type="button"
                        onClick={() => handleDeleteBlock(block.id)}
                        className="opacity-0 group-hover:opacity-100 text-charcoal/40 hover:text-red-600 transition-opacity p-0.5 ml-0.5 rounded cursor-pointer"
                        title="Remove variable block"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ) : (
                    /* Text Block */
                    <div className="flex items-center gap-1 px-2 py-1 rounded-xl text-xs font-mono bg-white text-charcoal-900 border border-slate-200 hover:border-slate-300 shadow-2xs transition-all">
                      {/* Drag Handle */}
                      <GripVertical className="w-3 h-3 text-slate-300 cursor-grab active:cursor-grabbing shrink-0" />

                      {/* Editable Text Input */}
                      <input
                        type="text"
                        value={block.text ?? ''}
                        onChange={(e) => handleTextChange(block.id, e.target.value)}
                        onBlur={handleTextBlur}
                        placeholder="space"
                        style={{
                          width: `${Math.max(2, (block.text || '').length + 1)}ch`,
                        }}
                        className="bg-transparent border-none outline-none font-mono text-xs text-charcoal-900 p-0 focus:ring-0 placeholder:text-charcoal/20"
                      />

                      {/* Remove Button */}
                      <button
                        type="button"
                        onClick={() => handleDeleteBlock(block.id)}
                        className="opacity-0 group-hover:opacity-100 text-charcoal/40 hover:text-red-600 transition-opacity p-0.5 rounded cursor-pointer"
                        title="Remove text block"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>
              </React.Fragment>
            );
          })}

          {/* Trailing drop indicator if dragging past last item */}
          {dropTargetIndex === blocks.length && (
            <div className="w-1 h-7 bg-indigo-600 rounded-full animate-pulse mx-0.5 shadow-xs" />
          )}
        </div>
      </div>

      {/* Author Formatting Controls */}
      <div className="space-y-2">
        {/* Checkbox 1: > 7 Authors Threshold Rule */}
        <div className="flex items-start gap-2.5 p-2.5 rounded-xl bg-white border border-border-light shadow-2xs">
          <input
            id="builder-truncate-authors"
            type="checkbox"
            checked={truncateAuthors}
            onChange={(e) => setTruncateAuthors(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-border-light text-indigo-brand focus:ring-indigo-brand cursor-pointer"
          />
          <label htmlFor="builder-truncate-authors" className="text-xs text-charcoal-900 cursor-pointer select-none">
            <span className="font-semibold block text-xs">
              First author shown for &gt; 7 authors (Threshold Rule)
            </span>
            <span className="text-[11px] text-charcoal/60 leading-normal block mt-0.5">
              If checked, citations with &gt; 7 authors only show the first author followed by{' '}
              <code className="font-mono text-indigo-brand">\textit&#123;et al.&#125;</code>. If unchecked, all authors are shown.
            </span>
          </label>
        </div>

        {/* Checkbox 2: And before last name */}
        <div className="flex items-start gap-2.5 p-2.5 rounded-xl bg-white border border-border-light shadow-2xs">
          <input
            id="builder-and-before-last"
            type="checkbox"
            checked={andBeforeLast}
            onChange={(e) => setAndBeforeLast(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-border-light text-indigo-brand focus:ring-indigo-brand cursor-pointer"
          />
          <label htmlFor="builder-and-before-last" className="text-xs text-charcoal-900 cursor-pointer select-none">
            <span className="font-semibold block text-xs">
              And before last name
            </span>
            <span className="text-[11px] text-charcoal/60 leading-normal block mt-0.5">
              If checked, insert &apos;and&apos; before the final author&apos;s name (e.g., A, B, and C).
            </span>
          </label>
        </div>
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
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] font-mono text-charcoal/60 uppercase tracking-wider flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5 text-indigo-brand" />
            <span>LIVE PREVIEW (GHOSH 2017 SAMPLE)</span>
          </span>

          <div className="flex items-center gap-2">
            {isValidating && (
              <span className="text-[10px] font-mono text-indigo-brand animate-pulse">
                Updating preview...
              </span>
            )}
            {displayPreview && (
              <button
                type="button"
                onClick={handleCopyPreview}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono text-charcoal/60 hover:text-indigo-brand transition-colors cursor-pointer"
                title="Copy preview to clipboard"
              >
                {copiedPreview ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-600" />
                    <span className="text-emerald-600">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-charcoal-800 bg-charcoal-900 text-cream p-3.5 font-mono text-xs overflow-auto max-h-36 select-all leading-relaxed shadow-inner">
          {displayPreview ? (
            <pre className="m-0 whitespace-pre-wrap">{displayPreview}</pre>
          ) : (
            <span className="text-charcoal/50 italic font-sans text-xs">
              {validationErrors.length > 0
                ? 'Fix template variables above to preview citation output.'
                : 'Rendering live citation preview...'}
            </span>
          )}
        </div>
      </div>

      {/* Bottom Action Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-border-light">
        {isEdit && !isProtected && onDelete ? (
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={onDelete}
            className="gap-1.5 text-red-600 border-red-200 bg-red-50/60 hover:bg-red-100/80 hover:text-red-700"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Delete Style</span>
          </Button>
        ) : (
          <div />
        )}

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            disabled={isSaving}
          >
            Cancel
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleSaveClick}
            disabled={isSaving || validationErrors.length > 0}
            className="gap-1.5"
          >
            {isSaving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Check className="w-3.5 h-3.5" />
            )}
            <span>{isEdit ? 'Save Changes' : 'Create Style'}</span>
          </Button>
        </div>
      </div>
    </div>
  );
};
