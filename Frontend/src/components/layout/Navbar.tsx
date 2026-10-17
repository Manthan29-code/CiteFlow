import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { LogOut, BookOpen, User as UserIcon, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { openTitleConfirmModal, openReviewModal } from '@/store/slices/jobsSlice';
import { Button } from '@/components/common/Button';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const waitingJobs = useAppSelector((state) =>
    Object.values(state.jobs.jobsById).filter(
      (j) => j.status === 'needs_title_confirmation' || j.status === 'needs_review'
    )
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
      <div className="flex items-center gap-3">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-charcoal-900 flex items-center justify-center text-white shadow-sm group-hover:scale-105 transition-transform">
            <BookOpen className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <span className="font-serif text-2xl font-bold tracking-tight text-charcoal-900">
              Cite<span className="italic font-normal text-indigo-brand">Flow</span>
            </span>
          </div>
        </Link>
      </div>

      {/* Center Label from Design Spec */}
      <div className="hidden md:flex items-center gap-2">
        <span className="font-mono text-xs uppercase tracking-[0.3em] text-charcoal/60">
          Organic Intelligence Library
        </span>
      </div>

      {/* Right User Controls & Status Indicator */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Needs Attention Indicator */}
        {waitingJobs.length > 0 && (
          <button
            type="button"
            onClick={handleAttentionClick}
            aria-label={`${waitingJobs.length} citation jobs need your input`}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-300 text-amber-900 text-xs font-mono tracking-wide hover:bg-amber-100 transition-colors animate-pulse cursor-pointer shadow-xs"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            <span>{waitingJobs.length} Need Input</span>
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
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white border border-border-light text-xs font-sans font-medium text-charcoal-800 shadow-sm">
            <UserIcon className="w-3.5 h-3.5 text-indigo-brand" />
            <span className="max-w-[140px] truncate">{user.email}</span>
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
