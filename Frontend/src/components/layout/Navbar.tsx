import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { LogOut, BookOpen, User as UserIcon, AlertTriangle, Menu, Moon, Sun } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openTitleConfirmModal, openReviewModal } from '@/store/slices/jobsSlice';
import { Button } from '@/components/common/Button';

interface NavbarProps {
  onToggleSidebar?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [isDarkMode, setIsDarkMode] = React.useState(() =>
    typeof window !== 'undefined' && window.localStorage.getItem('citeflow-theme') === 'dark'
  );

  const toggleTheme = () => {
    const nextTheme = !isDarkMode;
    setIsDarkMode(nextTheme);
    document.documentElement.classList.toggle('dark', nextTheme);
    window.localStorage.setItem('citeflow-theme', nextTheme ? 'dark' : 'light');
  };

  const jobsById = useAppSelector((state) => state.jobs.jobsById);
  const waitingJobs = React.useMemo(
    () =>
      Object.values(jobsById).filter(
        (j) => j.status === 'needs_title_confirmation' || j.status === 'needs_review'
      ),
    [jobsById]
  );

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleAttentionClick = () => {
    if (waitingJobs.length > 0) {
      const first = waitingJobs[0];
      if (first.status === 'needs_title_confirmation') {
        dispatch(openTitleConfirmModal(first.id));
      } else {
        dispatch(openReviewModal(first.id));
      }
    }
  };

  return (
    <header className="sticky top-0 z-30 w-full h-20 bg-cream/90 backdrop-blur-md border-b border-border-light px-4 sm:px-8 flex items-center justify-between">
      {/* Brand Logo */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button type="button" onClick={onToggleSidebar} aria-label="Toggle navigation sidebar" aria-controls="folder-navigation" className="md:hidden inline-flex items-center justify-center p-2 -ml-2 rounded-lg border border-border-light bg-white text-charcoal-800 hover:bg-cream-100 shrink-0">
          <Menu className="w-5 h-5" />
        </button>
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-charcoal-900 flex items-center justify-center text-white shadow-sm group-hover:scale-105 transition-transform">
            <BookOpen className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <span className="font-serif text-xl sm:text-2xl font-bold tracking-tight text-charcoal-900">
              Cite<span className="italic font-normal text-indigo-brand">Flow</span>
            </span>
          </div>
        </Link>
      </div>

      {/* Center Label from Design Spec */}
      <div className="hidden md:flex items-center gap-2">
        <span className="font-mono text-xs uppercase tracking-[0.3em] text-charcoal/60" style={{ fontSize: '20px' }}>
          Organic Intelligence Library
        </span>
      </div>

      {/* Right User Controls & Status Indicator */}
      <div className="flex items-center gap-1 sm:gap-3 shrink-0">
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to night mode'}
          aria-pressed={isDarkMode}
          title={isDarkMode ? 'Switch to light mode' : 'Switch to night mode'}
          className="inline-flex h-9 w-9 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-xl border border-border-light bg-white text-charcoal-800 hover:bg-cream-200 dark:border-border-dark dark:bg-charcoal-800 dark:text-cream-100 dark:hover:bg-charcoal-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-brand"
        >
          {isDarkMode ? <Sun className="h-4 w-4 sm:h-5 sm:w-5" /> : <Moon className="h-4 w-4 sm:h-5 sm:w-5" />}
        </button>
        {/* Needs Attention Indicator */}
        {waitingJobs.length > 0 && (
          <button
            type="button"
            onClick={handleAttentionClick}
            aria-label={`${waitingJobs.length} citation jobs need your input`}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-300 text-amber-900 text-xs font-mono tracking-wide hover:bg-amber-100 transition-colors animate-pulse cursor-pointer shadow-xs"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            <span>
              {waitingJobs.length} {waitingJobs.length === 1 ? 'Review Pending' : 'Reviews Pending'}
            </span>
          </button>
        )}

        {/* System Online Pill from design_rule.md */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-mono tracking-wide">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>System Online</span>
        </div>

        {/* User Badge */}
        {user && (
          <div className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1.5 rounded-xl bg-white border border-border-light text-xs font-sans font-medium text-charcoal-800 shadow-sm">
            <UserIcon className="w-3.5 h-3.5 text-indigo-brand" />
            <span className="hidden sm:inline max-w-[140px] truncate">{user.email}</span>
          </div>
        )}

        {/* Logout Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleLogout}
          aria-label="Log out"
          className="gap-1.5 text-xs text-charcoal-800 border-border-light hover:bg-red-50 hover:text-red-700 hover:border-red-200 transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Log Out</span>
        </Button>
      </div>
    </header>
  );
};
