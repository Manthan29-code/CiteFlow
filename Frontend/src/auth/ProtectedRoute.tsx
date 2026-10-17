import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Spinner } from '@/components/common/Spinner';

export const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, isCheckingSession } = useAuth();
  const location = useLocation();

  if (isCheckingSession) {
    return (
      <div className="min-h-screen bg-cream flex flex-col items-center justify-center">
        <Spinner size="lg" label="Restoring Session" />
      </div>
    );
  }

  if (!isAuthenticated) {
    const currentPath = location.pathname + location.search;
    return <Navigate to={`/login?next=${encodeURIComponent(currentPath)}`} replace />;
  }

  return <Outlet />;
};
