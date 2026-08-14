/**
 * Auth Context - User Authentication Management
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../lib/api';

interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone_number: string | null;
  profile_image: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  dark_mode: boolean;
  email_notifications: boolean;
  push_notifications: boolean;
  marketing_emails: boolean;
  is_admin: boolean;
  email_verified: boolean;
  has_complete_profile: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  updateUser: (data: Partial<User>) => void;
  refreshUser: () => Promise<void>;
}

interface RegisterData {
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  password: string;
  password_confirm: string;
  phone_number?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const refreshUser = useCallback(async () => {
    try {
      const response = await api.get('/auth/profile/');
      // ⚠️ Double check if your backend GET returns user directly or nested under response.data.user
      const userData = response.data.user ? response.data.user : response.data;
      setUser(userData);
    } catch (error) {
      // Both access and refresh tokens are completely invalid/expired
      // (or absent) - nothing to clear client-side anymore, since auth
      // now lives in httpOnly cookies the API itself manages.
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // On mount, there's no client-readable token to check anymore (it's an
  // httpOnly cookie) - the only way to know if a session exists is to ask
  // the API. `withCredentials: true` (see lib/api.ts) means the httpOnly
  // cookie, if any, is sent automatically; a 401 here just means "not
  // logged in", which refreshUser already handles by setting user: null.
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password: string) => {
    try {
      const response = await api.post('/auth/login/', { email, password });
      // Tokens are no longer in the response body - the API sets them as
      // httpOnly cookies directly on this response. Only `user` remains.
      const { user: loggedInUser } = response.data;

      setUser(loggedInUser);
      toast.success('Welcome back!');
      
      // Redirect based on role
      if (loggedInUser.is_admin) {
        navigate('/admin');
      } else {
        navigate('/');
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Login failed. Please try again.';
      toast.error(message);
      throw error;
    }
  };

  const register = async (data: RegisterData) => {
    try {
      await api.post('/auth/register/', data);
      toast.success('Registration successful! Please log in.');
      navigate('/login');
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Registration failed. Please try again.';
      toast.error(message);
      throw error;
    }
  };

  const logout = useCallback(() => {
    // Fire-and-forget: tells the API to blacklist the refresh token and
    // clear the httpOnly cookies. Client state is cleared immediately
    // either way so the UI doesn't wait on the network round-trip.
    api.post('/auth/logout/').catch(() => {
      // Even if this fails (e.g. already logged out / network hiccup),
      // proceed with clearing local state below - there's nothing further
      // to clean up client-side since no token is stored in JS anymore.
    });
    setUser(null);
    toast.success('Logged out successfully');
    navigate('/login');
  }, [navigate]);

  const updateUser = (data: Partial<User>) => {
    setUser((prev) => (prev ? { ...prev, ...data } : null));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        updateUser,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
