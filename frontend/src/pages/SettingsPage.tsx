/**
 * Settings Page
 */

import { motion } from 'framer-motion';
import { Moon, Sun, Bell, Mail, Smartphone } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import api from '../lib/api';
import { toast } from 'sonner';

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const { user, updateUser } = useAuth();

  const handleTogglePreference = async (key: string, value: boolean) => {
    try {
      await api.patch('/auth/preferences/', { [key]: value });
      updateUser({ [key]: value });
      toast.success('Preference updated');
    } catch (error) {
      toast.error('Failed to update preference');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        Settings
      </h1>

      {/* Appearance */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700"
      >
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Appearance
        </h2>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {theme === 'dark' ? (
              <Moon className="w-5 h-5 text-purple-600" />
            ) : (
              <Sun className="w-5 h-5 text-yellow-500" />
            )}
            <div>
              <p className="font-medium text-gray-900 dark:text-white">
                Dark Mode
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Toggle between light and dark theme
              </p>
            </div>
          </div>
          <button
            onClick={toggleTheme}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              theme === 'dark' ? 'bg-purple-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                theme === 'dark' ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </motion.div>

      {/* Notifications */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700 space-y-6"
      >
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Notifications
        </h2>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mail className="w-5 h-5 text-blue-500" />
            <div>
              <p className="font-medium text-gray-900 dark:text-white">
                Email Notifications
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Receive updates via email
              </p>
            </div>
          </div>
          <button
            onClick={() =>
              handleTogglePreference('email_notifications', !user?.email_notifications)
            }
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              user?.email_notifications ? 'bg-purple-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                user?.email_notifications ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Smartphone className="w-5 h-5 text-green-500" />
            <div>
              <p className="font-medium text-gray-900 dark:text-white">
                Push Notifications
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Receive push notifications
              </p>
            </div>
          </div>
          <button
            onClick={() =>
              handleTogglePreference('push_notifications', !user?.push_notifications)
            }
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              user?.push_notifications ? 'bg-purple-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                user?.push_notifications ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-orange-500" />
            <div>
              <p className="font-medium text-gray-900 dark:text-white">
                Marketing Emails
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Receive promotional offers
              </p>
            </div>
          </div>
          <button
            onClick={() =>
              handleTogglePreference('marketing_emails', !user?.marketing_emails)
            }
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              user?.marketing_emails ? 'bg-purple-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                user?.marketing_emails ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </motion.div>
    </div>
  );
}
