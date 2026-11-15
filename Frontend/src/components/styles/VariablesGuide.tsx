import React, { useState, useMemo } from 'react';
import {
  Copy,
  Check,
  Search,
  X,
  ArrowLeft,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppDispatch } from '@/store/hooks';
import { addToast } from '@/store/slices/uiSlice';

export interface VariableItem {
  tag: string;
  category: 'author' | 'publication' | 'identification';
  name: string;
  description: string;
  fallback?: string;
  example: string;
  supportsBold?: boolean;
  supportsLink?: boolean;
}

const VARIABLES: VariableItem[] = [
  // Author metadata
  {
    tag: 'surname',
    category: 'author',
    name: 'Author Surname / Family Name',
    description: 'Last name / family surname of each author. Combine with firstname in any order.',
    example: 'Ghosh',
  },
  {
    tag: 'firstname',
    category: 'author',
    name: 'Author Given Name / Initial',
    description: 'Given name or first initial of each author.',
    example: 'S.',
  },
  {
    tag: 'middle name',
    category: 'author',
    name: 'Author Middle Name / Initial',
    description: 'Middle name or middle initial of each author.',
    example: 'K.',
  },

  // Publication metadata
  {
    tag: 'title',
    category: 'publication',
    name: 'Paper Title',
    description: 'Full sanitized title of the document or research article.',
    example: 'Transition from single to multiple axial potential structure in expanding helicon plasma',
  },
  {
    tag: 'journal',
    category: 'publication',
    name: 'Journal Title',
    description: 'Full official publication title of the journal.',
    example: 'Journal of Physics D: Applied Physics',
  },
  {
    tag: 'journal abbr',
    category: 'publication',
    name: 'Journal Abbreviation',
    description: 'Standard ISO abbreviation for the journal.',
    fallback: 'Falls back to full journal title if absent',
    example: 'J Phys D Appl Phys',
  },
  {
    tag: 'volume',
    category: 'publication',
    name: 'Journal Volume',
    description: 'Volume designation. Supports Bold formatting toggle.',
    supportsBold: true,
    example: '50',
  },
  {
    tag: 'issue',
    category: 'publication',
    name: 'Journal Issue',
    description: 'Issue or edition number within volume. Supports Bold formatting toggle.',
    supportsBold: true,
    example: '6',
  },
  {
    tag: 'article number',
    category: 'publication',
    name: 'Article Identifier',
    description: 'Unique electronic article / CID identifier. Supports Bold formatting toggle.',
    fallback: 'Falls back to first page if absent',
    supportsBold: true,
    example: '065201',
  },
  {
    tag: 'first page',
    category: 'publication',
    name: 'First Page Number',
    description: 'Starting page number of printed article.',
    fallback: 'Falls back to article number if absent',
    example: '459',
  },
  {
    tag: 'year',
    category: 'publication',
    name: 'Publication Year',
    description: '4-digit publication calendar year.',
    example: '2017',
  },

  // Identification metadata
  {
    tag: 'citation key',
    category: 'identification',
    name: 'Citation Key',
    description: 'BibTeX identifier (first author surname + year) for \\bibitem.',
    example: 'Ghosh2017',
  },
  {
    tag: 'doi url',
    category: 'identification',
    name: 'Clickable DOI URL',
    description: 'Full HTTPS link to paper DOI. Supports Link formatting toggle.',
    supportsLink: true,
    example: 'https://doi.org/10.1088/1361-6463/aa5068',
  },
  {
    tag: 'doi',
    category: 'identification',
    name: 'Digital Object Identifier',
    description: 'Raw DOI identifier without URL scheme. Supports Link formatting toggle.',
    supportsLink: true,
    example: '10.1088/1361-6463/aa5068',
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
  const [selectedCategory, setSelectedCategory] = useState<'all' | 'author' | 'publication' | 'identification'>('all');
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
          message: `Copied "${tag}" to clipboard.`,
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

      {/* Author Representation & Visual Assembly */}
      <div className="p-3.5 sm:p-4 rounded-xl bg-cream-100 border border-border-light text-xs text-charcoal-800 space-y-3 shadow-2xs">
        <div className="flex items-center gap-2 font-serif font-bold text-sm text-charcoal-900">
          <Users className="w-4 h-4 text-indigo-brand shrink-0" />
          <span>Author Representation &amp; Visual Assembly</span>
        </div>
        <p className="text-[11px] font-sans text-charcoal/80 leading-relaxed">
          In the Visual Style Builder, citation formats are created by assembling metadata variables and text blocks. Author names are constructed using individual components (<code>surname</code>, <code>firstname</code>, <code>middle name</code>) instead of fixed strings. Drag and sequence these blocks with custom punctuation to format any journal style:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-sans">
          <div className="p-2.5 rounded-lg bg-white/90 border border-border-light space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-charcoal-900 text-xs">AMA / Vancouver Style</span>
              <span className="font-mono text-[10px] text-indigo-brand bg-indigo-50 px-1.5 py-0.5 rounded font-bold">surname firstname</span>
            </div>
            <div className="font-mono text-[10px] text-charcoal/70 bg-charcoal/5 p-1 rounded">
              Ghosh S, Chattopadhyay PK, Bora D.
            </div>
            <div className="text-[10px] text-charcoal/60">Surname first followed by given name initials, separated by commas.</div>
          </div>

          <div className="p-2.5 rounded-lg bg-white/90 border border-border-light space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-charcoal-900 text-xs">IEEE Style</span>
              <span className="font-mono text-[10px] text-indigo-brand bg-indigo-50 px-1.5 py-0.5 rounded font-bold">firstname . surname</span>
            </div>
            <div className="font-mono text-[10px] text-charcoal/70 bg-charcoal/5 p-1 rounded">
              S. Ghosh, P. K. Chattopadhyay, and D. Bora
            </div>
            <div className="text-[10px] text-charcoal/60">Given initial with dot first, then family surname. Uses Oxford comma &amp; &ldquo;and&rdquo;.</div>
          </div>

          <div className="p-2.5 rounded-lg bg-white/90 border border-border-light space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-charcoal-900 text-xs">Dotted Surname First</span>
              <span className="font-mono text-[10px] text-indigo-brand bg-indigo-50 px-1.5 py-0.5 rounded font-bold">surname firstname .</span>
            </div>
            <div className="font-mono text-[10px] text-charcoal/70 bg-charcoal/5 p-1 rounded">
              Ghosh S., Chattopadhyay P. K., Bora D.
            </div>
            <div className="text-[10px] text-charcoal/60">Surname first with dotted initial and trailing period.</div>
          </div>

          <div className="p-2.5 rounded-lg bg-white/90 border border-border-light space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-charcoal-900 text-xs">Full Name with Middle</span>
              <span className="font-mono text-[10px] text-indigo-brand bg-indigo-50 px-1.5 py-0.5 rounded font-bold">firstname middle name surname</span>
            </div>
            <div className="font-mono text-[10px] text-charcoal/70 bg-charcoal/5 p-1 rounded">
              S. K. Ghosh, P. K. Chattopadhyay
            </div>
            <div className="text-[10px] text-charcoal/60">First and middle initials or names preceding surname.</div>
          </div>
        </div>

        {/* Author Rule Checkboxes & Controls */}
        <div className="mt-2 pt-2 border-t border-border-light/70 space-y-1.5 text-[11px] font-sans text-charcoal-900 bg-white/80 p-2.5 rounded-lg border border-indigo-100">
          <div>
            <strong className="text-indigo-brand font-mono text-xs">Threshold Rule Checkbox (&gt; 7 Authors):</strong>
            <span className="text-charcoal/80 ml-1">
              When checked, publications with more than 7 authors will display only the first author followed by <code className="px-1 py-0.2 rounded bg-indigo-50 text-indigo-brand font-mono">\textit&#123;et al.&#125;</code>. When unchecked, all authors are shown regardless of count.
            </span>
          </div>

          <div className="pt-1 border-t border-indigo-50">
            <strong className="text-indigo-brand font-mono text-xs">&ldquo;And&rdquo; Before Last Name Checkbox:</strong>
            <span className="text-charcoal/80 ml-1">
              When checked, automatically inserts &ldquo;and&rdquo; before the final author in the citation list (e.g. <em>A, B, and C</em>).
            </span>
          </div>

          <div className="pt-1 border-t border-indigo-50">
            <strong className="text-indigo-brand font-mono text-xs">Drag-and-Drop Assembly:</strong>
            <span className="text-charcoal/80 ml-1">
              Add individual punctuation blocks (such as <code>.</code>, <code>,</code>, or spaces) directly between <code>surname</code> and <code>firstname</code> to achieve custom spacing.
            </span>
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
            placeholder="Search variables (e.g. surname, volume, doi url)..."
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
            Authors ({VARIABLES.filter((v) => v.category === 'author').length})
          </button>
          <button
            type="button"
            onClick={() => setSelectedCategory('publication')}
            className={cn(
              'px-2.5 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer',
              selectedCategory === 'publication'
                ? 'bg-white text-indigo-brand font-semibold shadow-xs'
                : 'text-charcoal/60 hover:text-charcoal'
            )}
          >
            Publication ({VARIABLES.filter((v) => v.category === 'publication').length})
          </button>
          <button
            type="button"
            onClick={() => setSelectedCategory('identification')}
            className={cn(
              'px-2.5 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer',
              selectedCategory === 'identification'
                ? 'bg-white text-indigo-brand font-semibold shadow-xs'
                : 'text-charcoal/60 hover:text-charcoal'
            )}
          >
            ID ({VARIABLES.filter((v) => v.category === 'identification').length})
          </button>
        </div>
      </div>

      {/* Desktop Table View (>= 640px) */}
      <div className="hidden sm:block rounded-xl border border-border-light bg-white overflow-hidden shadow-xs">
        <div className="max-h-[46vh] overflow-y-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-cream-100/80 sticky top-0 z-10 border-b border-border-light text-[10px] font-mono uppercase tracking-wider text-charcoal/60">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Variable Name</th>
                <th className="py-2.5 px-3 font-semibold">Example Output</th>
                <th className="py-2.5 px-3 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light/60">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={3} className="py-8 text-center text-charcoal/50 font-mono text-xs">
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
                      {/* Tag & Info */}
                      <td className="py-2.5 px-3 align-top font-mono">
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-indigo-50/70 border border-indigo-200/60 text-indigo-brand font-bold text-[11px]">
                              {item.tag}
                            </span>
                            {item.supportsBold && (
                              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-purple-50 text-purple-700 border border-purple-200">
                                Bold
                              </span>
                            )}
                            {item.supportsLink && (
                              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-blue-50 text-blue-700 border border-blue-200">
                                Link
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] font-sans text-charcoal/70">
                            {item.description}
                          </span>
                          {item.fallback && (
                            <span className="text-[10px] font-mono text-charcoal/50 italic">
                              {item.fallback}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Example Value */}
                      <td className="py-2.5 px-3 align-top">
                        <div className="p-1.5 rounded-lg bg-charcoal-900 text-cream font-mono text-[11px] leading-relaxed break-all select-all max-w-[420px]">
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
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="px-2 py-0.5 rounded-lg bg-indigo-50 text-indigo-brand font-mono font-bold text-[11px] border border-indigo-200 truncate">
                      {item.tag}
                    </span>
                    {item.supportsBold && (
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-purple-50 text-purple-700 border border-purple-200">
                        Bold
                      </span>
                    )}
                    {item.supportsLink && (
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-blue-50 text-blue-700 border border-blue-200">
                        Link
                      </span>
                    )}
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

                <div className="text-[11px] text-charcoal/70">
                  {item.description}
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
