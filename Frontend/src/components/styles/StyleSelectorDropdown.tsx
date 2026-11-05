import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Palette, Plus } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedStyleId } from '@/store/slices/stylesSlice';
import { openStyleManagerModal } from '@/store/slices/uiSlice';
import { cn } from '@/lib/utils';

export const StyleSelectorDropdown: React.FC = () => {
  const dispatch = useAppDispatch();
  const { styles, selectedStyleId } = useAppSelector((state) => state.styles);

  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentStyle = styles.find((s) => s.id === selectedStyleId) || styles[0];

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleSelect = (styleId: string) => {
    dispatch(setSelectedStyleId(styleId));
    setIsOpen(false);
  };

  const handleOpenManager = () => {
    setIsOpen(false);
    dispatch(openStyleManagerModal());
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        title={`Active Citation Style: ${currentStyle?.name || 'Default'}`}
        aria-label="Select Citation Style"
        className={cn(
          'inline-flex items-center gap-1.5 h-8 px-2.5 rounded-xl text-xs font-mono font-medium border transition-all cursor-pointer shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand',
          isOpen
            ? 'bg-cream-200 border-indigo-300 text-indigo-brand'
            : 'bg-white border-border-light text-charcoal-800 hover:border-indigo-200 hover:text-indigo-brand'
        )}
      >
        <Palette className="w-3.5 h-3.5 text-indigo-brand shrink-0" />
        <span className="truncate max-w-[100px] sm:max-w-[150px]">
          {currentStyle ? currentStyle.name : 'Style'}
        </span>
        <ChevronDown
          className={cn(
            'w-3 h-3 text-charcoal/50 transition-transform duration-150 shrink-0',
            isOpen && 'rotate-180 text-indigo-brand'
          )}
        />
      </button>

      {isOpen && (
        <div className="absolute left-0 sm:left-auto sm:right-0 mt-1 z-50 w-56 rounded-xl bg-white border border-border-light shadow-xl py-1 text-xs font-sans text-charcoal-800 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-1.5 text-[10px] font-mono text-charcoal/40 uppercase tracking-widest border-b border-border-light/60">
            Citation Style
          </div>

          <div className="max-h-56 overflow-y-auto py-1">
            {styles.map((style) => {
              const isSelected = selectedStyleId === style.id;
              return (
                <button
                  key={style.id}
                  type="button"
                  onClick={() => handleSelect(style.id)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-1.5 text-left text-xs transition-colors cursor-pointer',
                    isSelected
                      ? 'bg-indigo-50 text-indigo-brand font-semibold'
                      : 'hover:bg-cream-200 text-charcoal-800'
                  )}
                >
                  <span className="truncate mr-2">{style.name}</span>
                  {isSelected && <Check className="w-3.5 h-3.5 text-indigo-brand shrink-0" />}
                </button>
              );
            })}
          </div>

          <div className="border-t border-border-light/60 pt-1 mt-1">
            <button
              type="button"
              onClick={handleOpenManager}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-indigo-brand hover:bg-cream-200 transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Manage Styles...</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

