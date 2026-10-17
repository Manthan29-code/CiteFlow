import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Home, Folder as FolderIcon } from 'lucide-react';
import { Breadcrumb } from '@/types/api';

export interface BreadcrumbsProps {
  breadcrumbs: Breadcrumb[];
  currentFolderId?: string;
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ breadcrumbs }) => {
  const navigate = useNavigate();

  // If no breadcrumbs or just root
  const items = breadcrumbs && breadcrumbs.length > 0 ? breadcrumbs : [{ id: 'root', name: 'Root' }];

  return (
    <nav aria-label="Breadcrumbs" className="flex items-center space-x-1.5 text-xs font-mono tracking-wide py-2 overflow-x-auto whitespace-nowrap">
      {items.map((crumb, index) => {
        const isLast = index === items.length - 1;
        const isRoot = index === 0 || crumb.id === 'root' || crumb.name.toLowerCase() === 'root';

        const handleClick = () => {
          if (isLast) return;
          if (isRoot) {
            navigate('/');
          } else {
            navigate(`/folders/${crumb.id}`);
          }
        };

        return (
          <div key={crumb.id || index} className="flex items-center">
            {index > 0 && (
              <ChevronRight className="w-3.5 h-3.5 mx-1 text-charcoal/30 shrink-0" aria-hidden="true" />
            )}
            <button
              onClick={handleClick}
              disabled={isLast}
              aria-current={isLast ? 'page' : undefined}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-lg transition-colors ${
                isLast
                  ? 'font-semibold text-charcoal-900 bg-black/5 cursor-default'
                  : 'text-charcoal/60 hover:text-indigo-brand hover:bg-cream-200'
              }`}
            >
              {isRoot ? (
                <Home className="w-3.5 h-3.5 text-indigo-brand shrink-0" />
              ) : (
                <FolderIcon className="w-3.5 h-3.5 text-indigo-brand/70 shrink-0" />
              )}
              <span className="truncate max-w-[160px]">{isRoot ? 'Library' : crumb.name}</span>
            </button>
          </div>
        );
      })}
    </nav>
  );
};
