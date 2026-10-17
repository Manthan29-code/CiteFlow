import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Folder as FolderIcon,
  FolderOpen,
  ChevronRight,
  ChevronDown,
  Plus,
  Home,
  Layers,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openNewFolderModal } from '@/store/slices/uiSlice';
import { getFolderDetails, getRootFolder } from '@/api/folders';
import { Folder } from '@/types/api';
import { cn } from '@/lib/utils';

interface TreeNodeProps {
  id: string;
  name: string;
  depth: number;
  currentFolderId: string;
  onSelect: (id: string) => void;
}

const TreeNode: React.FC<TreeNodeProps> = ({ id, name, depth, currentFolderId, onSelect }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [children, setChildren] = useState<Folder[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const isSelected = currentFolderId === id || (id === 'root' && currentFolderId === 'root');

  const toggleExpand = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isExpanded) {
      setIsExpanded(true);
      if (children.length === 0) {
        setIsLoading(true);
        try {
          const res = id === 'root' ? await getRootFolder() : await getFolderDetails(id);
          setChildren(res.folders || []);
        } catch {
          // silently handle error in tree
        } finally {
          setIsLoading(false);
        }
      }
    } else {
      setIsExpanded(false);
    }
  };

  const handleClick = () => {
    onSelect(id);
  };

  return (
    <div role="treeitem" aria-expanded={isExpanded} aria-selected={isSelected} className="select-none">
      <div
        onClick={handleClick}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
        className={cn(
          'group flex items-center justify-between py-2 pr-2 rounded-xl text-xs font-sans font-medium cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand',
          isSelected
            ? 'bg-indigo-brand/10 text-indigo-brand font-semibold shadow-xs border border-indigo-brand/20'
            : 'text-charcoal-800 hover:bg-cream-200 hover:text-charcoal-900'
        )}
      >
        <div className="flex items-center gap-2 truncate">
          <button
            type="button"
            onClick={toggleExpand}
            className="p-0.5 rounded text-charcoal/40 hover:text-charcoal-900 transition-colors"
            aria-label={isExpanded ? 'Collapse folder' : 'Expand folder'}
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
          </button>

          {id === 'root' ? (
            <Home className={cn('w-4 h-4 shrink-0', isSelected ? 'text-indigo-brand' : 'text-charcoal/50')} />
          ) : isExpanded ? (
            <FolderOpen className={cn('w-4 h-4 shrink-0', isSelected ? 'text-indigo-brand' : 'text-indigo-brand/70')} />
          ) : (
            <FolderIcon className={cn('w-4 h-4 shrink-0', isSelected ? 'text-indigo-brand' : 'text-charcoal/50')} />
          )}

          <span className="truncate">{name}</span>
        </div>

        {isLoading && (
          <span className="w-2 h-2 rounded-full border border-indigo-brand border-t-transparent animate-spin mr-1" />
        )}
      </div>

      {isExpanded && children.length > 0 && (
        <div role="group" className="space-y-0.5">
          {children.map((child) => (
            <TreeNode
              key={child.id}
              id={child.id}
              name={child.name}
              depth={depth + 1}
              currentFolderId={currentFolderId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const Sidebar: React.FC = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const currentFolderId = useAppSelector((state) => state.explorer.currentFolderId);
  const [rootFolders, setRootFolders] = useState<Folder[]>([]);

  useEffect(() => {
    getRootFolder()
      .then((res) => {
        setRootFolders(res.folders || []);
      })
      .catch(() => {});
  }, [currentFolderId]);

  const handleSelectFolder = (id: string) => {
    if (id === 'root') {
      navigate('/');
    } else {
      navigate(`/folders/${id}`);
    }
  };

  return (
    <aside
      aria-label="Folder Navigation Sidebar"
      className="w-64 border-r border-border-light bg-cream flex flex-col shrink-0 h-[calc(100vh-5rem)] sticky top-20 overflow-y-auto"
    >
      {/* Sidebar Header & New Folder Button */}
      <div className="p-4 border-b border-border-light flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-brand" />
          <span className="font-mono text-xs uppercase tracking-[0.2em] font-semibold text-charcoal-900">
            Navigation
          </span>
        </div>
        <button
          onClick={() => dispatch(openNewFolderModal())}
          title="Create New Folder"
          className="p-1.5 rounded-lg text-charcoal/60 hover:text-indigo-brand hover:bg-cream-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Folder Tree */}
      <div role="tree" className="p-3 space-y-1 flex-1 overflow-y-auto">
        <TreeNode
          id="root"
          name="Library Root"
          depth={0}
          currentFolderId={currentFolderId}
          onSelect={handleSelectFolder}
        />

        {rootFolders.map((folder) => (
          <TreeNode
            key={folder.id}
            id={folder.id}
            name={folder.name}
            depth={0}
            currentFolderId={currentFolderId}
            onSelect={handleSelectFolder}
          />
        ))}
      </div>

      {/* Storage info footer */}
      <div className="p-4 border-t border-border-light bg-cream-100/50">
        <div className="text-[11px] font-mono text-charcoal/50 uppercase tracking-widest mb-1">
          Cloud Storage
        </div>
        <div className="text-xs font-sans text-charcoal-700">
          PDF Library Active
        </div>
      </div>
    </aside>
  );
};
