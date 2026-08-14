/**
 * API Client - Axios instance with interceptors
 */

import axios from 'axios';

// NOTE: must match the var name actually set in .env / .env.production
// (VITE_API_BASE_URL).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Auth now travels as httpOnly cookies set by the API (see
  // accounts/views.py) instead of an Authorization header built from a
  // token in localStorage - `withCredentials` is what makes the browser
  // actually attach those cookies on cross-origin requests to the API.
  withCredentials: true,
});

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

// Request interceptor - attach the CSRF double-submit header for unsafe
// methods. The access/refresh JWTs themselves are httpOnly (unreadable
// from JS, and sent automatically by the browser via withCredentials) -
// only the separate, non-httpOnly `csrf_token` cookie is readable here,
// by design (see accounts/authentication.py for why this is needed on
// top of httpOnly cookies).
api.interceptors.request.use(
  (config) => {
    const method = (config.method || 'get').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      const csrfToken = readCookie('csrf_token');
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't tried to refresh token yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // No body needed - the refresh token is read straight from its
        // own httpOnly cookie server-side. A successful response sets
        // fresh access/refresh/csrf cookies automatically; there's
        // nothing to store here.
        await axios.post(`${API_BASE_URL}/auth/refresh/`, {}, { withCredentials: true });

        // Retry the original request - the new access-token cookie will
        // be attached automatically via withCredentials.
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed (refresh cookie missing/expired/blacklisted) -
        // the API has already cleared any stale cookies it could; just
        // reflect that in app state and send the user to log in again.
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
