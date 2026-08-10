/**
 * Main Layout - Sidebar Navigation for Desktop, Bottom Nav for Mobile
 */

import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home,
  ShoppingBag,
  Search,
  Heart,
  ShoppingCart,
  User,
  Package,
  Wallet,
  Settings,
  LogOut,
  Menu,
  X,
  Sun,
  Moon,
  Store
} from 'lucide-react';
import { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import { cn } from '../lib/utils';

const sidebarLinks = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/products', icon: ShoppingBag, label: 'Products' },
  { path: '/search', icon: Search, label: 'Search' },
  { path: '/wishlist', icon: Heart, label: 'Wishlist' },
  { path: '/cart', icon: ShoppingCart, label: 'Cart' },
  { path: '/orders', icon: Package, label: 'Orders' },
  { path: '/wallet', icon: Wallet, label: 'Wallet' },
  { path: '/profile', icon: User, label: 'Profile' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

const bottomNavLinks = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/products', icon: ShoppingBag, label: 'Shop' },
  { path: '/wallet', icon: Wallet, label: 'Wallet' },
  { path: '/cart', icon: ShoppingCart, label: 'Cart' },
  { path: '/profile', icon: User, label: 'Profile' },
];

// Helper to safely build image URL from backend path
const getImageUrl = (path: string | undefined | null): string => {
  if (!path) return '/default-avatar.png';
  // If the API already returns an absolute URL, use it as-is
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  // If it's a relative path, prepend the API base URL from env (fallback to current origin)
  const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin;
  // Ensure no double slashes when joining
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${cleanPath}`;
};

export default function MainLayout() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { user, isAuthenticated, logout } = useAuth();
  const { cartCount } = useCart();
  const location = useLocation();

  const isAdmin = user?.is_admin;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:flex lg:w-72 lg:flex-col lg:border-r lg:border-gray-200 lg:bg-white dark:lg:bg-gray-800 dark:lg:border-gray-700">
        {/* Logo */}
        <div className="flex h-16 items-center border-b border-gray-200 dark:border-gray-700 px-6">
          <NavLink to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center">
              <Store className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900 dark:text-white">
              GadgetHub
            </span>
          </NavLink>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-4 py-6">
          <ul className="space-y-1">
            {sidebarLinks.map((link) => (
              <li key={link.path}>
                <NavLink
                  to={link.path}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/25'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
                    )
                  }
                >
                  <link.icon className="w-5 h-5" />
                  <span>{link.label}</span>
                  {link.path === '/cart' && cartCount > 0 && (
                    <span className="ml-auto bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                      {cartCount}
                    </span>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>

          {/* Admin Link */}
          {isAdmin && (
            <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
              <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Admin
              </p>
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/25'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
                  )
                }
              >
                <Store className="w-5 h-5" />
                <span>Dashboard</span>
              </NavLink>
            </div>
          )}
        </nav>

        {/* User Section */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </span>
          </div>

          {isAuthenticated ? (
            <div className="flex items-center gap-3">
              <img
                src={getImageUrl(user?.profile_image)}
                alt={user?.full_name}
                className="w-10 h-10 rounded-full object-cover border-2 border-purple-600"
                onError={(e) => { (e.target as HTMLImageElement).src = '/default-avatar.png'; }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {user?.full_name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user?.email}
                </p>
              </div>
              <button
                onClick={logout}
                className="p-2 text-gray-400 hover:text-red-500 transition-colors"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <NavLink
                to="/login"
                className="flex-1 px-4 py-2 text-sm font-medium text-purple-600 bg-purple-50 dark:bg-purple-900/20 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors text-center"
              >
                Login
              </NavLink>
              <NavLink
                to="/register"
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 transition-colors text-center"
              >
                Register
              </NavLink>
            </div>
          )}
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between h-16 px-4">
          <NavLink to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
              <Store className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900 dark:text-white">
              GadgetHub
            </span>
          </NavLink>

          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
            >
              <nav className="px-4 py-4">
                <ul className="space-y-1">
                  {sidebarLinks.map((link) => (
                    <li key={link.path}>
                      <NavLink
                        to={link.path}
                        onClick={() => setIsMobileMenuOpen(false)}
                        className={({ isActive }) =>
                          cn(
                            'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200',
                            isActive
                              ? 'bg-purple-600 text-white'
                              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                          )
                        }
                      >
                        <link.icon className="w-5 h-5" />
                        <span>{link.label}</span>
                        {link.path === '/cart' && cartCount > 0 && (
                          <span className="ml-auto bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                            {cartCount}
                          </span>
                        )}
                      </NavLink>
                    </li>
                  ))}
                </ul>

                {isAuthenticated && (
                  <button
                    onClick={() => {
                      logout();
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 mt-4 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors"
                  >
                    <LogOut className="w-5 h-5" />
                    <span>Logout</span>
                  </button>
                )}
              </nav>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* Main Content */}
      <main className="lg:pl-72 pt-16 lg:pt-0 pb-20 lg:pb-0 min-h-screen">
        <div className="p-4 lg:p-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 safe-area-pb">
        <div className="flex items-center justify-around h-16">
          {bottomNavLinks.map((link) => (
            <NavLink
              key={link.path}
              to={link.path}
              className={({ isActive }) =>
                cn(
                  'flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors',
                  isActive
                    ? 'text-purple-600'
                    : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
                )
              }
            >
              <div className="relative">
                <link.icon className="w-6 h-6" />
                {link.path === '/cart' && cartCount > 0 && (
                  <span className="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] font-bold w-4 h-4 flex items-center justify-center rounded-full">
                    {cartCount > 9 ? '9+' : cartCount}
                  </span>
                )}
              </div>
              <span className="text-xs">{link.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}