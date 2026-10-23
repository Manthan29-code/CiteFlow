import React, { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from '@/store';
import { useAuth } from '@/hooks/useAuth';
import { AppRoutes } from '@/routes';
import { ToastContainer } from '@/components/common/ToastContainer';

const AppContent: React.FC = () => {
  const { checkSession } = useAuth();

  useEffect(() => {
    // Restore the user's theme preference before they start navigating.
    const savedTheme = window.localStorage.getItem('citeflow-theme');
    document.documentElement.classList.toggle('dark', savedTheme === 'dark');

    // Attempt session restore on application load
    checkSession();
  }, [checkSession]);

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppRoutes />
      <ToastContainer />
    </BrowserRouter>
  );
};

export default function App() {
  return (
    <Provider store={store}>
      <AppContent />
    </Provider>
  );
}
