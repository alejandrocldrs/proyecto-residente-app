import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import api, { setAuthToken } from '../services/api';

interface User {
  id: string;
  username: string;
  email: string;
  gender?: string;
  subscription_type?: string;
  points?: number;
  rank?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  loadStoredAuth: () => Promise<void>;
}

interface RegisterData {
  username: string;
  email: string;
  password: string;
  gender: string;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  isAuthenticated: false,

  loadStoredAuth: async () => {
    try {
      const token = await SecureStore.getItemAsync('auth_token');
      const userJson = await SecureStore.getItemAsync('user_data');
      if (token && userJson) {
        const user = JSON.parse(userJson);
        setAuthToken(token);
        set({ token, user, isAuthenticated: true });
      }
    } catch {
      // No stored credentials
    }
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const response = await api.post('/api/auth/login', { email, password });
      const { token, user } = response.data;
      setAuthToken(token);
      await SecureStore.setItemAsync('auth_token', token);
      await SecureStore.setItemAsync('user_data', JSON.stringify(user));
      set({ token, user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  register: async (data) => {
    set({ isLoading: true });
    try {
      const response = await api.post('/api/auth/register', data);
      const { token, user } = response.data;
      setAuthToken(token);
      await SecureStore.setItemAsync('auth_token', token);
      await SecureStore.setItemAsync('user_data', JSON.stringify(user));
      set({ token, user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    setAuthToken(null);
    await SecureStore.deleteItemAsync('auth_token');
    await SecureStore.deleteItemAsync('user_data');
    set({ token: null, user: null, isAuthenticated: false });
  },
}));
