import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import api, { setAuthToken } from '../services/api';

interface User {
  id: string;
  full_name: string;
  email: string;
  gender: string;
  is_admin: boolean;
  is_approved: boolean;
  profile_image: string | null;
  universidad: string | null;
  subscription_expires: string | null;
  account_type: string; // 'trial' | 'premium' | 'free'
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
  full_name: string;
  email: string;
  password: string;
  gender: string;
}

const fetchCurrentUser = async (): Promise<User> => {
  const response = await api.get('/api/auth/me');
  return response.data;
};

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
      const loginRes = await api.post('/api/auth/login', { email, password });
      const token: string = loginRes.data.access_token;
      setAuthToken(token);
      const user = await fetchCurrentUser();
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
      await api.post('/api/auth/register', data);
      // Register doesn't return a token — login immediately after
      const loginRes = await api.post('/api/auth/login', {
        email: data.email,
        password: data.password,
      });
      const token: string = loginRes.data.access_token;
      setAuthToken(token);
      const user = await fetchCurrentUser();
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
