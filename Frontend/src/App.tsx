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
    // Attempt session restore on application load
    checkSession();
  }, [checkSession]);

  return (
    <BrowserRouter>
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
