import axios from 'axios';

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'https://landing-residente.emergent.host';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach auth token to every request if present
api.interceptors.request.use((config) => {
  const token = globalAuthToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Will be set by the auth store after login
let globalAuthToken: string | null = null;
export const setAuthToken = (token: string | null) => {
  globalAuthToken = token;
};

export default api;
