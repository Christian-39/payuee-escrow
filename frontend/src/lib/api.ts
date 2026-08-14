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

// Requests to these paths must NOT trigger the auto-refresh-and-redirect
// flow below. In particular /auth/profile/ is called on every single page
// load (AuthContext's refreshUser, on mount) purely to check "is there a
// valid session?" - for a logged-out visitor that's an *expected* 401,
// not a session that "expired mid-use". Previously that 401 fell through
// to the same refresh-then-redirect logic as everything else: refresh
// also 401'd (no refresh cookie for an anonymous visitor), and the
// catch below did `window.location.href = '/login'` unconditionally -
// including when already sitting on /login, which just reassigning
// location.href *still forces a reload* even to the same URL. That
// produced an infinite reload loop on first paint for every anonymous
// visitor (matches "login page refreshes immediately", and everything
// downstream of it - cart/wishlist/upload/search all failing - was
// simply the page never staying alive long enough to finish any of those
// requests).
const AUTH_CHECK_PATHS = ['/auth/profile/', '/auth/refresh/', '/auth/login/', '/auth/register/', '/auth/logout/'];

function isAuthCheckRequest(url?: string): boolean {
  if (!url) return false;
  return AUTH_CHECK_PATHS.some((path) => url.includes(path));
}

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status !== 401 || originalRequest._retry || isAuthCheckRequest(originalRequest?.url)) {
      return Promise.reject(error);
    }

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
      // Refresh failed (refresh cookie missing/expired/blacklisted) - the
      // user genuinely isn't authenticated. Only force navigation if
      // we're not already on /login (or /register), so this can never
      // turn into a self-reload loop; AuthContext's own state (user:
      // null) already reflects "logged out" for everything else on the
      // page without a hard navigation.
      const publicAuthPages = ['/login', '/register'];
      if (!publicAuthPages.includes(window.location.pathname)) {
        window.location.href = '/login';
      }
      return Promise.reject(refreshError);
    }
  }
);

export default api;
