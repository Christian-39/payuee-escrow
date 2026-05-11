/**
 * Profile Page
 * Displays user profile, wallet summary, and account stats.
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Camera,
  Mail,
  Phone,
  MapPin,
  Package,
  Heart,
  Star,
  Wallet,
  ArrowDownLeft,
  ArrowUpRight,
  Eye,
  EyeOff,
  Landmark,
  Copy,
  RefreshCw,
  ChevronRight,
  Clock,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { toast } from 'sonner';

interface UserStats {
  orders_count: number;
  wishlist_count: number;
  reviews_count: number;
}

interface WalletBalance {
  status: string;
  wallet_balance: number;
  currency: string;
}

interface WalletTransaction {
  id: string;
  type: 'credit' | 'debit';
  amount: number;
  description: string;
  status: 'completed' | 'pending' | 'failed';
  created_at: string;
}

export default function ProfilePage() {
  const { user, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // User stats
  const [stats, setStats] = useState<UserStats>({
    orders_count: 0,
    wishlist_count: 0,
    reviews_count: 0,
  });
  const [statsLoading, setStatsLoading] = useState(true);

  // Wallet state
  const [walletBalance, setWalletBalance] = useState<WalletBalance | null>(null);
  const [walletTransactions, setWalletTransactions] = useState<WalletTransaction[]>([]);
  const [walletLoading, setWalletLoading] = useState(true);
  const [showWalletBalance, setShowWalletBalance] = useState(true);
  const [isRefreshingWallet, setIsRefreshingWallet] = useState(false);

  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    phone_number: user?.phone_number || '',
    address: user?.address || '',
    city: user?.city || '',
    state: user?.state || '',
    country: user?.country || '',
    postal_code: user?.postal_code || '',
  });

  // Fetch user stats
  useEffect(() => {
    const fetchUserStats = async () => {
      try {
        const [ordersRes, wishlistRes, reviewsRes] = await Promise.allSettled([
          api.get('/orders/count/'),
          api.get('/wishlist/count/'),
          api.get('/reviews/count/'),
        ]);

        setStats({
          orders_count: ordersRes.status === 'fulfilled' ? ordersRes.value.data.count || 0 : 0,
          wishlist_count: wishlistRes.status === 'fulfilled' ? wishlistRes.value.data.count || 0 : 0,
          reviews_count: reviewsRes.status === 'fulfilled' ? reviewsRes.value.data.count || 0 : 0,
        });
      } catch (error) {
        console.error('Failed to fetch user stats:', error);
      } finally {
        setStatsLoading(false);
      }
    };

    if (user) {
      fetchUserStats();
    }
  }, [user]);

  // Fetch wallet data
  useEffect(() => {
    const fetchWalletData = async () => {
      try {
        setWalletLoading(true);
        const [balanceRes, txRes] = await Promise.allSettled([
          api.get('/payments/wallet/balance/'),
          api.get('/payments/wallet-transactions/'),
        ]);

        if (balanceRes.status === 'fulfilled' && balanceRes.value.data.success) {
          setWalletBalance(balanceRes.value.data);
        }

        if (txRes.status === 'fulfilled') {
          setWalletTransactions(txRes.value.data.results || txRes.value.data || []);
        }
      } catch (error) {
        console.error('Failed to fetch wallet data:', error);
      } finally {
        setWalletLoading(false);
      }
    };

    if (user) {
      fetchWalletData();
    }
  }, [user]);

  const refreshWallet = async () => {
    setIsRefreshingWallet(true);
    try {
      const [balanceRes, txRes] = await Promise.allSettled([
        api.get('/payments/wallet/balance/'),
        api.get('/payments/wallet-transactions/'),
      ]);

      if (balanceRes.status === 'fulfilled' && balanceRes.value.data.success) {
        setWalletBalance(balanceRes.value.data);
      }

      if (txRes.status === 'fulfilled') {
        setWalletTransactions(txRes.value.data.results || txRes.value.data || []);
      }
      toast.success('Wallet refreshed');
    } catch (error) {
      toast.error('Failed to refresh wallet');
    } finally {
      setIsRefreshingWallet(false);
    }
  };

  const formatAmount = (amount: number | undefined, currency: string = 'NGN') => {
    if (amount === undefined || amount === null) return '—';
    const mainUnit = amount / 100;
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
    }).format(mainUnit);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-NG', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await api.patch('/auth/profile/update/', formData);
      updateUser(response.data.user);
      toast.success('Profile updated successfully');
      setIsEditing(false);
    } catch (error) {
      toast.error('Failed to update profile');
    }
  };

  const BASE_URL = 'http://127.0.0.1:8000';

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const uploadData = new FormData();
    uploadData.append('profile_image', file);

    try {
      const response = await api.post('/auth/profile/image/', uploadData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      updateUser({ profile_image: response.data.profile_image });
      toast.success('Profile image updated');
    } catch (error) {
      toast.error('Failed to upload image');
    } finally {
      setIsUploading(false);
    }
  };

  if (!user) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 dark:text-gray-400">Please login to view your profile</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Profile Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700"
      >
        <div className="flex flex-col md:flex-row items-center gap-6">
          {/* Avatar */}
          <div className="relative">
            <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-purple-600">
              <img
                src={user.profile_image ? `${BASE_URL}${user.profile_image}` : '/default-avatar.png'}
                alt={user.full_name}
                className="w-full h-full object-cover"
              />
            </div>
            <label className="absolute bottom-0 right-0 p-2 bg-purple-600 text-white rounded-full cursor-pointer hover:bg-purple-700 transition-colors">
              <Camera className="w-5 h-5" />
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
            </label>
            {isUploading && (
              <div className="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              </div>
            )}
          </div>

          {/* Info */}
          <div className="text-center md:text-left flex-1">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {user.full_name}
            </h1>
            <p className="text-gray-500 dark:text-gray-400">{user.email}</p>
            <div className="flex flex-wrap justify-center md:justify-start gap-4 mt-4">
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <Package className="w-4 h-4" />
                <span>{statsLoading ? '...' : `${stats.orders_count} Orders`}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <Heart className="w-4 h-4" />
                <span>{statsLoading ? '...' : `${stats.wishlist_count} Wishlist`}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <Star className="w-4 h-4" />
                <span>{statsLoading ? '...' : `${stats.reviews_count} Reviews`}</span>
              </div>
            </div>
          </div>

          {/* Edit Button */}
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="px-6 py-2.5 bg-purple-600 text-white font-medium rounded-xl hover:bg-purple-700 transition-colors"
          >
            {isEditing ? 'Cancel' : 'Edit Profile'}
          </button>
        </div>
      </motion.div>

      {/* ── WALLET SUMMARY CARD ── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800"
      >
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1920&q=80')] bg-cover bg-center opacity-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-purple-900/60 to-transparent" />

        <div className="relative p-6 lg:p-8">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-white/20 backdrop-blur-sm rounded-xl">
                <Wallet className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-purple-200 text-xs uppercase tracking-wider font-medium">
                  Payuee Wallet
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <h2 className="text-3xl font-bold text-white">
                    {walletLoading ? (
                      <span className="inline-block w-28 h-8 bg-white/20 rounded animate-pulse" />
                    ) : showWalletBalance ? (
                      formatAmount(walletBalance?.wallet_balance, walletBalance?.currency)
                    ) : (
                      '****'
                    )}
                  </h2>
                  <button
                    onClick={() => setShowWalletBalance(!showWalletBalance)}
                    className="p-1.5 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
                  >
                    {showWalletBalance ? (
                      <EyeOff className="w-3.5 h-3.5 text-white" />
                    ) : (
                      <Eye className="w-3.5 h-3.5 text-white" />
                    )}
                  </button>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={refreshWallet}
                disabled={isRefreshingWallet}
                className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 text-white ${isRefreshingWallet ? 'animate-spin' : ''}`} />
              </button>
              <Link
                to="/wallet"
                className="flex items-center gap-1 px-3 py-2 bg-white/20 backdrop-blur-sm rounded-lg text-white text-sm font-medium hover:bg-white/30 transition-colors"
              >
                Manage
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-1.5 mb-1">
                <TrendingUp className="w-3.5 h-3.5 text-green-300" />
                <span className="text-purple-200 text-xs">Credited</span>
              </div>
              <p className="text-sm font-semibold text-white">
                {walletLoading
                  ? '—'
                  : formatAmount(
                      walletTransactions
                        .filter((t) => t.type === 'credit')
                        .reduce((sum, t) => sum + t.amount, 0),
                      walletBalance?.currency
                    )}
              </p>
            </div>
            <div className="p-3 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-1.5 mb-1">
                <TrendingDown className="w-3.5 h-3.5 text-red-300" />
                <span className="text-purple-200 text-xs">Debited</span>
              </div>
              <p className="text-sm font-semibold text-white">
                {walletLoading
                  ? '—'
                  : formatAmount(
                      walletTransactions
                        .filter((t) => t.type === 'debit')
                        .reduce((sum, t) => sum + t.amount, 0),
                      walletBalance?.currency
                    )}
              </p>
            </div>
            <div className="p-3 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-1.5 mb-1">
                <Clock className="w-3.5 h-3.5 text-yellow-300" />
                <span className="text-purple-200 text-xs">Pending</span>
              </div>
              <p className="text-sm font-semibold text-white">
                {walletLoading
                  ? '—'
                  : formatAmount(
                      walletTransactions
                        .filter((t) => t.status === 'pending')
                        .reduce((sum, t) => sum + t.amount, 0),
                      walletBalance?.currency
                    )}
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Profile Form / Contact Info */}
      {isEditing ? (
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          onSubmit={handleSubmit}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700 space-y-6"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Edit Profile
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                First Name
              </label>
              <input
                type="text"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Last Name
              </label>
              <input
                type="text"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Phone Number
              </label>
              <input
                type="tel"
                name="phone_number"
                value={formData.phone_number}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Address
              </label>
              <input
                type="text"
                name="address"
                value={formData.address}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                City
              </label>
              <input
                type="text"
                name="city"
                value={formData.city}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                State
              </label>
              <input
                type="text"
                name="state"
                value={formData.state}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Country
              </label>
              <input
                type="text"
                name="country"
                value={formData.country}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Postal Code
              </label>
              <input
                type="text"
                name="postal_code"
                value={formData.postal_code}
                onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div className="flex gap-4">
            <button
              type="submit"
              className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors"
            >
              Save Changes
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="px-8 py-3 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-semibold rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        </motion.form>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
            Contact Information
          </h2>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <Mail className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Email</p>
                <p className="text-gray-900 dark:text-white">{user.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Phone className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Phone</p>
                <p className="text-gray-900 dark:text-white">
                  {user.phone_number || 'Not provided'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <MapPin className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Address</p>
                <p className="text-gray-900 dark:text-white">
                  {user.address
                    ? `${user.address}, ${user.city}, ${user.state}, ${user.country} ${user.postal_code}`
                    : 'Not provided'}
                </p>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}