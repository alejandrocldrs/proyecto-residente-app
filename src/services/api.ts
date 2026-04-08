import axios from 'axios';

// TODO: Replace with deployed backend URL once backend is hosted
// During development, if running backend locally: 'http://localhost:8001'
export const API_BASE_URL = 'https://your-backend-url.com';

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
