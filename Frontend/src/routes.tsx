import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '@/auth/ProtectedRoute';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { ExplorerPage } from '@/pages/ExplorerPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Auth Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected Explorer Routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<ExplorerPage />} />
        <Route path="/folders/:folderId" element={<ExplorerPage />} />
      </Route>

      {/* 404 Fallback */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};
