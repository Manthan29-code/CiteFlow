import { apiClient } from './client';
import { User } from '@/types/api';

export interface AuthCredentials {
  email: string;
  password: string;
}

export async function login(credentials: AuthCredentials): Promise<User> {
  return apiClient<User>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

export async function register(credentials: AuthCredentials): Promise<User> {
  return apiClient<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

export async function getMe(): Promise<User> {
  return apiClient<User>('/auth/me', {
    method: 'GET',
  });
}

export async function logout(): Promise<{ message: string }> {
  return apiClient<{ message: string }>('/auth/logout', {
    method: 'POST',
  });
}

export async function refreshToken(): Promise<{ message: string }> {
  return apiClient<{ message: string }>('/auth/refresh', {
    method: 'POST',
  });
}
