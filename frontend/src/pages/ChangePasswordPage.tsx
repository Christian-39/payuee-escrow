/**
 * Change Password Page
 *
 * Previously linked from ProfilePage ("/profile/change-password") but the
 * route and component did not exist, so the link rendered a blank page.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Lock, Eye, EyeOff, ArrowLeft, Loader2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../lib/api';

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [show, setShow] = useState({ old: false, new: false, confirm: false });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    if (newPassword !== confirmPassword) {
      setErrors({ new_password_confirm: "Passwords don't match." });
      return;
    }

    setIsSubmitting(true);
    try {
      // Field names must match ChangePasswordSerializer on the backend.
      await api.put('/auth/password/change/', {
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: confirmPassword,
      });
      toast.success('Password changed successfully');
      navigate('/profile');
    } catch (error: any) {
      const data = error.response?.data;
      if (data && typeof data === 'object') {
        const fieldErrors: Record<string, string> = {};
        Object.entries(data).forEach(([key, val]) => {
          fieldErrors[key] = Array.isArray(val) ? val[0] : String(val);
        });
        setErrors(fieldErrors);
      } else {
        toast.error('Failed to change password');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const fields: Array<{
    key: 'old' | 'new' | 'confirm';
    label: string;
    value: string;
    setValue: (v: string) => void;
    errorKey: string;
  }> = [
    { key: 'old', label: 'Current Password', value: oldPassword, setValue: setOldPassword, errorKey: 'old_password' },
    { key: 'new', label: 'New Password', value: newPassword, setValue: setNewPassword, errorKey: 'new_password' },
    { key: 'confirm', label: 'Confirm New Password', value: confirmPassword, setValue: setConfirmPassword, errorKey: 'new_password_confirm' },
  ];

  return (
    <div className="max-w-md mx-auto">
      <Link to="/profile" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Profile
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Lock className="w-5 h-5 text-blue-600" />
          </div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Change Password</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {fields.map(({ key, label, value, setValue, errorKey }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{label}</label>
              <div className="relative">
                <input
                  type={show[key] ? 'text' : 'password'}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  required
                  className="w-full px-4 py-3 pr-11 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => ({ ...s, [key]: !s[key] }))}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {show[key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors[errorKey] && <p className="mt-1.5 text-sm text-red-600 dark:text-red-400">{errors[errorKey]}</p>}
            </div>
          ))}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors disabled:opacity-50"
          >
            {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {isSubmitting ? 'Changing...' : 'Change Password'}
          </button>
        </form>
      </motion.div>
    </div>
  );
}
