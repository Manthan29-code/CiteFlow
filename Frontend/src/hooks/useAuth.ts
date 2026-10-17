import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { loginUser, registerUser, logoutUser, clearAuthError, checkAuthSession } from '@/store/slices/authSlice';
import { AuthCredentials } from '@/api/auth';

export function useAuth() {
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isCheckingSession, isLoading, error } = useAppSelector(
    (state) => state.auth
  );

  const login = useCallback(
    async (credentials: AuthCredentials) => {
      const result = await dispatch(loginUser(credentials));
      return loginUser.fulfilled.match(result);
    },
    [dispatch]
  );

  const register = useCallback(
    async (credentials: AuthCredentials) => {
      const result = await dispatch(registerUser(credentials));
      return registerUser.fulfilled.match(result);
    },
    [dispatch]
  );

  const logout = useCallback(async () => {
    await dispatch(logoutUser());
  }, [dispatch]);

  const checkSession = useCallback(async () => {
    await dispatch(checkAuthSession());
  }, [dispatch]);

  const clearError = useCallback(() => {
    dispatch(clearAuthError());
  }, [dispatch]);

  return {
    user,
    isAuthenticated,
    isCheckingSession,
    isLoading,
    error,
    login,
    register,
    logout,
    checkSession,
    clearError,
  };
}
