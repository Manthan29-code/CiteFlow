import React, { useState, useMemo } from 'react';
import {
  Copy,
  Check,
  Search,
  X,
  ArrowLeft,
  Users,
  FileText,
  Info,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppDispatch } from '@/store/hooks';
import { addToast } from '@/store/slices/uiSlice';

export interface VariableItem {
  tag: string;
  category: 'author' | 'metadata';
  name: string;
  description: string;
  fallback?: string;
  example: string;
}

const VARIABLES: VariableItem[] = [
  // Author representations
  {
    tag: '<AUTHORS_LAST_FIRST(.)>',
    category: 'author',
    name: 'Surname First, Dotted Initials',
    description: 'Surname first, dotted initials separated by commas.',
    example: 'Ghosh S., Chattopadhyay P. K., Bora D.',
  },
  {
    tag: '<AUTHORS_LAST_FIRST()>',
    category: 'author',
    name: 'Surname First, Compressed Initials',
    description: 'Surname first, undotted compressed initials separated by commas (Vancouver / AMA style).',
    example: 'Ghosh S, Chattopadhyay PK, Bora D.',
  },
  {
    tag: '<AUTHORS_FIRST(.)_LAST>',
    category: 'author',
    name: 'Dotted Initials First, Surname',
    description: 'Dotted initials first, surname with Oxford comma and "and" (IEEE style).',
    example: 'S. Ghosh, P. K. Chattopadhyay, and D. Bora',
  },
  {
    tag: '<AUTHORS_FIRST()_LAST>',
    category: 'author',
    name: 'Undotted Initials First, Surname',
    description: 'Undotted initials first, surname with "and".',
    example: 'S Ghosh, P K Chattopadhyay, and D Bora',
  },
  {
    tag: '<AUTHORS>',
    category: 'author',
    name: 'Default CiteFlow IOP Author List',
    description: 'Default CiteFlow IOP style author format.',
    example: 'Ghosh S, Chattopadhyay P K and Bora D',
  },

  // Bibliographic metadata
  {
    tag: '<CITATION_KEY>',
    category: 'metadata',
    name: 'Citation Key',
    description: 'First author surname + year identifier for \\bibitem.',
    example: 'Ghosh2017',
  },
  {
    tag: '<TITLE>',
    category: 'metadata',
    name: 'Paper Title',
    description: 'Full sanitized document title.',
    example: 'Transition from single to multiple axial potential structure in expanding helicon plasma',
  },
  {
    tag: '<JOURNAL>',
    category: 'metadata',
    name: 'Journal Name',
    description: 'Full standard journal publication title.',
    example: 'Journal of Physics D: Applied Physics',
  },
  {
    tag: '<JOURNAL_ABBREVIATION>',
    category: 'metadata',
    name: 'ISO Journal Abbreviation',
    description: 'Standard ISO abbreviation for the journal.',
    fallback: 'Falls back to <JOURNAL> if absent',
    example: 'J Phys D Appl Phys',
  },
  {
    tag: '<YEAR>',
    category: 'metadata',
    name: 'Publication Year',
    description: '4-digit publication calendar year.',
    example: '2017',
  },
  {
    tag: '<VOLUME>',
    category: 'metadata',
    name: 'Journal Volume',
    description: 'Journal volume designation.',
    example: '50',
  },
  {
    tag: '<ISSUE>',
    category: 'metadata',
    name: 'Journal Issue',
    description: 'Issue or edition number within volume.',
    example: '6',
  },
  {
    tag: '<ARTICLE_NUMBER>',
    category: 'metadata',
    name: 'Article Identifier',
    description: 'Unique electronic article / CID number.',
    fallback: 'Falls back to <FIRST_PAGE> if absent',
    example: '065201',
  },
  {
    tag: '<FIRST_PAGE>',
    category: 'metadata',
    name: 'First Page Number',
    description: 'Initial page of printed article span.',
    fallback: 'Falls back to <ARTICLE_NUMBER> if absent',
    example: '459',
  },
  {
    tag: '<LOCATOR>',
    category: 'metadata',
    name: 'Smart Locator (Page / Article ID)',
    description: 'Automatically chooses <ARTICLE_NUMBER> or <FIRST_PAGE> based on availability.',
    fallback: 'Auto-picks article_number or first_page',
    example: '065201',
  },
  {
    tag: '<DOI>',
    category: 'metadata',
    name: 'Raw Digital Object Identifier',
    description: 'DOI identifier without http/https protocol prefix.',
    example: '10.1088/1361-6463/aa5068',
  },
  {
    tag: '<DOI_URL>',
    category: 'metadata',
    name: 'Clickable DOI URL',
    description: 'Complete HTTPS DOI link, ideal for \\href{<DOI_URL>}{...}.',
    example: 'https://doi.org/10.1088/1361-6463/aa5068',
  },
];

export interface VariablesGuideProps {
  onBack: () => void;
  backLabel?: string;
  onSelectTag?: (tag: string) => void;
}

export const VariablesGuide: React.FC<VariablesGuideProps> = ({
  onBack,
  backLabel = 'Back to Styles List',
  onSelectTag,
}) => {
  const dispatch = useAppDispatch();
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<'all' | 'author' | 'metadata'>('all');
  const [copiedTag, setCopiedTag] = useState<string | null>(null);

  const filteredItems = useMemo(() => {
    return VARIABLES.filter((item) => {
      const matchCategory = selectedCategory === 'all' || item.category === selectedCategory;
      if (!matchCategory) return false;
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (
        item.tag.toLowerCase().includes(q) ||
        item.name.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.example.toLowerCase().includes(q) ||
        (item.fallback && item.fallback.toLowerCase().includes(q))
      );
    });
  }, [search, selectedCategory]);

  const handleCopyTag = async (tag: string) => {
    try {
      await navigator.clipboard.writeText(tag);
      setCopiedTag(tag);
      dispatch(
        addToast({
          type: 'success',
          message: `Copied ${tag} to clipboard.`,
        })
      );
      setTimeout(() => setCopiedTag(null), 2000);
      if (onSelectTag) {
        onSelectTag(tag);
      }
    } catch {
      dispatch(
        addToast({
          type: 'error',
          message: 'Clipboard access denied.',
        })
      );
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Navigation & Title Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border-light">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-mono text-charcoal/70 hover:text-indigo-brand transition-colors cursor-pointer self-start"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>{backLabel}</span>
        </button>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-charcoal/40 uppercase tracking-widest hidden sm:inline">
            Variables Reference
          </span>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-indigo-50 border border-indigo-200 text-indigo-brand font-medium">
            {filteredItems.length} Available
          </span>
        </div>
      </div>

      {/* Author Threshold Rule Alert Box */}
      <div className="p-3.5 sm:p-4 rounded-xl bg-cream-100 border border-border-light text-xs text-charcoal-800 space-y-1.5 shadow-2xs">
        <div className="flex items-center gap-2 font-serif font-bold text-sm text-charcoal-900">
          <Users className="w-4 h-4 text-indigo-brand shrink-0" />
          <span>Author Representation &amp; Generalization Rules</span>
        </div>
        <p className="text-[11px] font-sans text-charcoal/80 leading-relaxed">
          CiteFlow supports multiple standard author formatting patterns. Choose initial placement, dotting, and separators using the uppercase tag variants below.
        </p>
        <div className="mt-2 pt-2 border-t border-border-light/70 flex items-start gap-2 text-[11px] font-mono text-indigo-950 bg-white/70 p-2.5 rounded-lg border border-indigo-100">
          <Sparkles className="w-4 h-4 text-indigo-brand shrink-0 mt-0.5" />
          <div>
            <strong className="text-indigo-brand">Threshold Rule:</strong> Correctly preserves all authors for{' '}
            <code className="px-1 py-0.2 rounded bg-indigo-50 text-indigo-brand font-semibold">&le; 7</code> authors, and prints the first author +{' '}
            <code className="px-1 py-0.2 rounded bg-indigo-50 text-indigo-brand font-semibold">\textit&#123;et al.&#125;</code> when authors exceed{' '}
            <code className="px-1 py-0.2 rounded bg-indigo-50 text-indigo-brand font-semibold">&gt; 7</code>.
          </div>
        </div>
      </div>

      {/* Search and Category Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-charcoal/40" />
          <input
            type="text"
            placeholder="Search variables (e.g. authors, doi, locator)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-8 py-1.5 text-xs bg-white border border-border-light rounded-xl text-charcoal-900 placeholder:text-charcoal/40 focus:outline-none focus:ring-2 focus:ring-indigo-brand shadow-xs font-mono"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              aria-label="Clear search"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-charcoal/40 hover:text-charcoal cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1 p-1 bg-cream-200 rounded-xl border border-border-light shrink-0">
          <button
            type="button"
            onClick={() => setSelectedCategory('all')}
            className={cn(
              'px-2.5 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer',
              selectedCategory === 'all'
                ? 'bg-white text-indigo-brand font-semibold shadow-xs'
                : 'text-charcoal/60 hover:text-charcoal'
            )}
          >
            All ({VARIABLES.length})
          </button>
          <button
            type="button"
            onClick={() => setSelectedCategory('author')}
            className={cn(
              'px-2.5 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer',
              selectedCategory === 'author'
                ? 'bg-white text-indigo-brand font-semibold shadow-xs'
                : 'text-charcoal/60 hover:text-charcoal'
            )}
          >
            Authors
          </button>
          <button
            type="button"
            onClick={() => setSelectedCategory('metadata')}
            className={cn(
              'px-2.5 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer',
              selectedCategory === 'metadata'
                ? 'bg-white text-indigo-brand font-semibold shadow-xs'
                : 'text-charcoal/60 hover:text-charcoal'
            )}
          >
            Metadata
          </button>
        </div>
      </div>

      {/* Desktop Table View (>= 640px) */}
      <div className="hidden sm:block rounded-xl border border-border-light bg-white overflow-hidden shadow-xs">
        <div className="max-h-[46vh] overflow-y-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-cream-100/80 sticky top-0 z-10 border-b border-border-light text-[10px] font-mono uppercase tracking-wider text-charcoal/60">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Variable Tag</th>
                <th className="py-2.5 px-3 font-semibold">Description &amp; Rules</th>
                <th className="py-2.5 px-3 font-semibold">Example Value</th>
                <th className="py-2.5 px-3 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light/60">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-charcoal/50 font-mono text-xs">
                    No variables matched your search query.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => {
                  const isCopied = copiedTag === item.tag;
                  return (
                    <tr
                      key={item.tag}
                      className="hover:bg-cream-50/80 transition-colors group"
                    >
                      {/* Tag */}
                      <td className="py-2.5 px-3 align-top font-mono">
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-indigo-50/70 border border-indigo-200/60 text-indigo-brand font-bold text-[11px]">
                          <span>{item.tag}</span>
                        </div>
                      </td>

                      {/* Description & Fallback */}
                      <td className="py-2.5 px-3 align-top max-w-[280px]">
                        <div className="font-semibold text-charcoal-900 text-xs mb-0.5">
                          {item.name}
                        </div>
                        <div className="text-charcoal/70 text-[11px] leading-relaxed">
                          {item.description}
                        </div>
                        {item.fallback && (
                          <div className="mt-1 inline-flex items-center gap-1 text-[10px] font-mono text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                            <Info className="w-3 h-3 text-amber-600 shrink-0" />
                            <span>{item.fallback}</span>
                          </div>
                        )}
                      </td>

                      {/* Example Value */}
                      <td className="py-2.5 px-3 align-top max-w-[260px]">
                        <div className="p-1.5 rounded-lg bg-charcoal-900 text-cream font-mono text-[11px] leading-relaxed break-all select-all">
                          {item.example}
                        </div>
                      </td>

                      {/* Action Button */}
                      <td className="py-2.5 px-3 align-top text-right">
                        <button
                          type="button"
                          onClick={() => handleCopyTag(item.tag)}
                          title={`Copy ${item.tag}`}
                          className={cn(
                            'inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer shadow-2xs border',
                            isCopied
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                              : 'bg-white hover:bg-indigo-50 text-charcoal-800 hover:text-indigo-brand border-border-light'
                          )}
                        >
                          {isCopied ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-600" />
                              <span className="text-[10px]">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3 text-charcoal/50 group-hover:text-indigo-brand" />
                              <span className="text-[10px]">Copy</span>
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile Card View (< 640px) */}
      <div className="sm:hidden space-y-2 max-h-[50vh] overflow-y-auto pr-0.5">
        {filteredItems.length === 0 ? (
          <div className="py-8 text-center text-charcoal/50 font-mono text-xs p-4 bg-white rounded-xl border border-border-light">
            No variables matched your search query.
          </div>
        ) : (
          filteredItems.map((item) => {
            const isCopied = copiedTag === item.tag;
            return (
              <div
                key={item.tag}
                className="p-3 rounded-xl border border-border-light bg-white shadow-2xs space-y-2 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="px-2 py-0.5 rounded-lg bg-indigo-50 text-indigo-brand font-mono font-bold text-[11px] border border-indigo-200 truncate">
                    {item.tag}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleCopyTag(item.tag)}
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-mono transition-colors cursor-pointer border shrink-0',
                      isCopied
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                        : 'bg-white text-charcoal-700 hover:text-indigo-brand border-border-light'
                    )}
                  >
                    {isCopied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    <span>{isCopied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>

                <div>
                  <div className="font-semibold text-charcoal-900 text-xs">{item.name}</div>
                  <div className="text-charcoal/70 text-[11px] mt-0.5 leading-relaxed">
                    {item.description}
                  </div>
                  {item.fallback && (
                    <div className="mt-1 text-[10px] font-mono text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 inline-block">
                      {item.fallback}
                    </div>
                  )}
                </div>

                <div className="p-1.5 rounded-lg bg-charcoal-900 text-cream font-mono text-[10px] break-all">
                  <span className="text-cream/40 block text-[9px] uppercase tracking-wider mb-0.5">Example Output:</span>
                  {item.example}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

