/**
 * Profile Page with Payuee Location Integration
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Camera, Mail, Phone, MapPin, Package, Heart, Star, Wallet,
  Eye, EyeOff, RefreshCw, ChevronRight, ChevronDown, Loader2,
  Clock, TrendingUp, TrendingDown, ShoppingBag, Lock,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { toast } from 'sonner';
import PayueePinModal from '../pages/PayueePinModal';
import { usePayueeLocation } from '../hooks/usePayueeLocation';
import { cn } from '../lib/utils';

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

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading: authLoading, updateUser } = useAuth();
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const [stats, setStats] = useState<UserStats>({ orders_count: 0, wishlist_count: 0, reviews_count: 0 });
  const [statsLoading, setStatsLoading] = useState(true);

  const [walletBalance, setWalletBalance] = useState<WalletBalance | null>(null);
  const [walletTransactions, setWalletTransactions] = useState<WalletTransaction[]>([]);
  const [walletLoading, setWalletLoading] = useState(true);
  const [showWalletBalance, setShowWalletBalance] = useState(true);
  const [isRefreshingWallet, setIsRefreshingWallet] = useState(false);

  const [showPinModal, setShowPinModal] = useState(false);
  const [hasPayueePin, setHasPayueePin] = useState(false);

  const {
    states, cities, selectedState, selectedCity,
    loadingStates, loadingCities, locationError,
    setSelectedState, setSelectedCity,
  } = usePayueeLocation();

  const [stateOpen, setStateOpen] = useState(false);
  const [cityOpen, setCityOpen] = useState(false);

  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    phone_number: user?.phone_number || '',
    address: user?.address || '',
    city: user?.city || '',
    state: user?.state || '',
    country: user?.country || 'Nigeria',
    postal_code: user?.postal_code || '',
    latitude: user?.latitude || '',
    longitude: user?.longitude || '',
  });

  // Redirect unauthenticated users
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      toast.error('Please login to view your profile');
      navigate('/login');
    }
  }, [authLoading, isAuthenticated, navigate]);

  // Check if user has Payuee PIN set
  useEffect(() => {
    const checkPinStatus = async () => {
      try {
        const response = await api.get('/auth/profile/');
        setHasPayueePin(!!response.data.payuee_transaction_pin);
      } catch (error) {
        console.error('Failed to check PIN status:', error);
      }
    };
    if (user) checkPinStatus();
  }, [user]);

  // Sync existing profile location with Payuee dropdowns
  useEffect(() => {
    if (isEditing && user?.state && states.length > 0 && !selectedState) {
      setSelectedState(user.state);
    }
  }, [isEditing, user?.state, states.length, selectedState, setSelectedState]);

  useEffect(() => {
    if (isEditing && user?.city && cities.length > 0 && !selectedCity) {
      const matched = cities.find(c => c.display === user.city || c.city === user.city);
      if (matched) setSelectedCity(matched);
    }
  }, [isEditing, user?.city, cities, selectedCity, setSelectedCity]);

  useEffect(() => {
    const fetchUserStats = async () => {
      try {
        const [ordersRes, wishlistRes, reviewsRes] = await Promise.allSettled([
          api.get('/orders/count/'), api.get('/wishlist/count/'), api.get('/reviews/count/'),
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
    if (user) fetchUserStats();
  }, [user]);

  useEffect(() => {
    const fetchWalletData = async () => {
      try {
        setWalletLoading(true);
        const [balanceRes, txRes] = await Promise.allSettled([
          api.get('/payments/wallet/balance/'), api.get('/payments/wallet-transactions/'),
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
    if (user) fetchWalletData();
  }, [user]);

  const refreshWallet = async () => {
    setIsRefreshingWallet(true);
    try {
      const [balanceRes, txRes] = await Promise.allSettled([
        api.get('/payments/wallet/balance/'), api.get('/payments/wallet-transactions/'),
      ]);
      if (balanceRes.status === 'fulfilled' && balanceRes.value.data.success) setWalletBalance(balanceRes.value.data);
      if (txRes.status === 'fulfilled') setWalletTransactions(txRes.value.data.results || txRes.value.data || []);
      toast.success('Wallet refreshed');
    } catch {
      toast.error('Failed to refresh wallet');
    } finally {
      setIsRefreshingWallet(false);
    }
  };

  const formatAmount = (amount: number | undefined, currency: string = 'NGN') => {
    if (amount === undefined || amount === null) return '—';
    return new Intl.NumberFormat('en-NG', { style: 'currency', currency, minimumFractionDigits: 2 }).format(amount / 100);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-NG', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleStateSelect = (state: string) => {
    setSelectedState(state);
    setStateOpen(false);
    setCityOpen(false);
    setSelectedCity(null);
    setFormData(prev => ({ ...prev, state, city: '', latitude: '', longitude: '' }));
  };

  const handleCitySelect = (city: any) => {
    if (!city) return;
    setSelectedCity(city);
    setCityOpen(false);
    setFormData(prev => ({ ...prev, city: city.display, latitude: String(city.latitude), longitude: String(city.longitude) }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await api.patch('/auth/profile/update/', formData);
      updateUser(response.data.user);
      toast.success('Profile updated successfully');
      setIsEditing(false);
    } catch {
      toast.error('Failed to update profile');
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    const uploadData = new FormData();
    uploadData.append('profile_image', file);
    try {
      const response = await api.post('/auth/profile/image/', uploadData, { headers: { 'Content-Type': 'multipart/form-data' } });
      // Accept either profile_image or image_url from backend response
      const imagePath = response.data.profile_image || response.data.image_url;
      updateUser({ profile_image: imagePath });
      toast.success('Profile image updated');
    } catch {
      toast.error('Failed to upload image');
    } finally {
      setIsUploading(false);
    }
  };

  const handlePinSet = (pin: string) => {
    setHasPayueePin(true);
    toast.success('Payuee PIN set successfully!');
  };

  // Show loading state while auth is being checked
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-12 h-12 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin" />
      </div>
    );
  }

  // Show login prompt for unauthenticated users (fallback if redirect hasn't happened yet)
  if (!isAuthenticated) {
    return (
      <div className="text-center py-16">
        <div className="w-24 h-24 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
          <ShoppingBag className="w-12 h-12 text-purple-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Your Profile is Waiting
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
          Please login to view your profile, manage your wallet, and track your orders
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            to="/login"
            className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors"
          >
            Login
          </Link>
          <Link
            to="/register"
            className="px-8 py-3 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-semibold rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Register
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Profile Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700">
        <div className="flex flex-col md:flex-row items-center gap-6">
          <div className="relative">
            <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-purple-600">
              <img 
                src={getImageUrl(user?.profile_image)} 
                alt={user?.full_name} 
                className="w-full h-full object-cover" 
                onError={(e) => { (e.target as HTMLImageElement).src = '/default-avatar.png'; }}
              />
            </div>
            <label className="absolute bottom-0 right-0 p-2 bg-purple-600 text-white rounded-full cursor-pointer hover:bg-purple-700 transition-colors">
              <Camera className="w-5 h-5" />
              <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
            </label>
            {isUploading && (
              <div className="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              </div>
            )}
          </div>
          <div className="text-center md:text-left flex-1">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{user?.full_name}</h1>
            <p className="text-gray-500 dark:text-gray-400">{user?.email}</p>
            <div className="flex flex-wrap justify-center md:justify-start gap-4 mt-4">
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"><Package className="w-4 h-4" /><span>{statsLoading ? '...' : `${stats.orders_count} Orders`}</span></div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"><Heart className="w-4 h-4" /><span>{statsLoading ? '...' : `${stats.wishlist_count} Wishlist`}</span></div>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"><Star className="w-4 h-4" /><span>{statsLoading ? '...' : `${stats.reviews_count} Reviews`}</span></div>
            </div>
          </div>
          <button onClick={() => setIsEditing(!isEditing)} className="px-6 py-2.5 bg-purple-600 text-white font-medium rounded-xl hover:bg-purple-700 transition-colors">
            {isEditing ? 'Cancel' : 'Edit Profile'}
          </button>
        </div>
      </motion.div>

      {/* Wallet Card */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800">
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1920&q=80')] bg-cover bg-center opacity-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-purple-900/60 to-transparent" />
        <div className="relative p-6 lg:p-8">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-white/20 backdrop-blur-sm rounded-xl"><Wallet className="w-5 h-5 text-white" /></div>
              <div>
                <p className="text-purple-200 text-xs uppercase tracking-wider font-medium">Payuee Wallet</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <h2 className="text-3xl font-bold text-white">
                    {walletLoading ? <span className="inline-block w-28 h-8 bg-white/20 rounded animate-pulse" /> :
                      showWalletBalance ? formatAmount(walletBalance?.wallet_balance, walletBalance?.currency) : '****'}
                  </h2>
                  <button onClick={() => setShowWalletBalance(!showWalletBalance)} className="p-1.5 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                    {showWalletBalance ? <EyeOff className="w-3.5 h-3.5 text-white" /> : <Eye className="w-3.5 h-3.5 text-white" />}
                  </button>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={refreshWallet} disabled={isRefreshingWallet} className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors disabled:opacity-50">
                <RefreshCw className={`w-4 h-4 text-white ${isRefreshingWallet ? 'animate-spin' : ''}`} />
              </button>
              <Link to="/wallet" className="flex items-center gap-1 px-3 py-2 bg-white/20 backdrop-blur-sm rounded-lg text-white text-sm font-medium hover:bg-white/30 transition-colors">
                Manage<ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-1.5 mb-1"><TrendingUp className="w-3.5 h-3.5 text-green-300" /><span className="text-purple-200 text-xs">Credited</span></div>
              <p className="text-sm font-semibold text-white">{walletLoading ? '—' : formatAmount(walletTransactions.filter(t => t.type === 'credit').reduce((sum, t) => sum + t.amount, 0), walletBalance?.currency)}</p>
            </div>
            <div className="p-3 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-1.5 mb-1"><TrendingDown className="w-3.5 h-3.5 text-red-300" /><span className="text-purple-200 text-xs">Debited</span></div>
              <p className="text-sm font-semibold text-white">{walletLoading ? '—' : formatAmount(walletTransactions.filter(t => t.type === 'debit').reduce((sum, t) => sum + t.amount, 0), walletBalance?.currency)}</p>
            </div>
            <div className="p-3 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-1.5 mb-1"><Clock className="w-3.5 h-3.5 text-yellow-300" /><span className="text-purple-200 text-xs">Pending</span></div>
              <p className="text-sm font-semibold text-white">{walletLoading ? '—' : formatAmount(walletTransactions.filter(t => t.status === 'pending').reduce((sum, t) => sum + t.amount, 0), walletBalance?.currency)}</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Security Settings Card */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
        className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Security Settings</h2>

        <div className="space-y-4">
          {/* Change Password Row */}
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Lock className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white">Password</h3>
                <p className="text-sm text-gray-500">Change your account password</p>
              </div>
            </div>
            <Link
              to="/profile/change-password"
              className="flex items-center gap-1 px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
            >
              Change <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Payuee PIN Row */}
          <div className={cn(
            "flex items-center justify-between p-4 rounded-xl border",
            hasPayueePin 
              ? "bg-green-50 dark:bg-green-900/10 border-green-100 dark:border-green-800/30"
              : "bg-amber-50 dark:bg-amber-900/10 border-amber-100 dark:border-amber-800/30"
          )}>
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-2 rounded-lg",
                hasPayueePin
                  ? "bg-green-100 dark:bg-green-900/30"
                  : "bg-amber-100 dark:bg-amber-900/30"
              )}>
                <Lock className={cn(
                  "w-5 h-5",
                  hasPayueePin ? "text-green-600" : "text-amber-600"
                )} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-900 dark:text-white">Payuee Transaction PIN</h3>
                  {hasPayueePin && (
                    <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs font-medium rounded-full">
                      Active
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500">
                  {hasPayueePin 
                    ? 'Your PIN is set and ready for escrow orders'
                    : 'Required for placing Payuee escrow orders'}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowPinModal(true)}
              className={cn(
                "flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
                hasPayueePin
                  ? "bg-green-600 text-white hover:bg-green-700"
                  : "bg-amber-600 text-white hover:bg-amber-700"
              )}
            >
              {hasPayueePin ? 'Update PIN' : 'Set PIN'}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </motion.div>

      {/* Profile Form / Contact Info */}
      {isEditing ? (
        <motion.form initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} onSubmit={handleSubmit}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700 space-y-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Edit Profile</h2>

          {locationError && <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-xl">{locationError}</div>}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">First Name</label>
              <input type="text" name="first_name" value={formData.first_name} onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Last Name</label>
              <input type="text" name="last_name" value={formData.last_name} onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Phone Number</label>
              <input type="tel" name="phone_number" value={formData.phone_number} onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Address</label>
              <input type="text" name="address" value={formData.address} onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>

            {/* State Dropdown */}
            <div className="relative">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">State *</label>
              <button type="button" onClick={() => setStateOpen(!stateOpen)} disabled={loadingStates}
                className={cn('w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-700 border rounded-xl text-left transition-all',
                  stateOpen ? 'border-purple-500 ring-2 ring-purple-500/20' : 'border-gray-200 dark:border-gray-600')}>
                <span className={selectedState ? 'text-gray-900 dark:text-white' : 'text-gray-400'}>{selectedState || 'Select state'}</span>
                {loadingStates ? <Loader2 className="w-4 h-4 animate-spin text-gray-400" /> : <ChevronDown className={cn('w-4 h-4 text-gray-400 transition-transform', stateOpen && 'rotate-180')} />}
              </button>
              {stateOpen && (
                <div className="absolute z-50 w-full mt-1 max-h-52 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg">
                  {states.map(state => (
                    <button key={state} type="button" onClick={() => handleStateSelect(state)}
                      className={cn('w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors', selectedState === state && 'bg-purple-50 dark:bg-purple-900/20 text-purple-600')}>
                      {state}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* City Dropdown */}
            <div className="relative">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">City / Area *</label>
              <button type="button" onClick={() => selectedState && setCityOpen(!cityOpen)} disabled={!selectedState || loadingCities}
                className={cn('w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-700 border rounded-xl text-left transition-all',
                  !selectedState && 'opacity-50 cursor-not-allowed',
                  cityOpen ? 'border-purple-500 ring-2 ring-purple-500/20' : 'border-gray-200 dark:border-gray-600')}>
                <span className={selectedCity ? 'text-gray-900 dark:text-white' : 'text-gray-400'}>
                  {selectedCity?.display || (selectedState ? 'Select area' : 'Select state first')}
                </span>
                {loadingCities ? <Loader2 className="w-4 h-4 animate-spin text-gray-400" /> : <ChevronDown className={cn('w-4 h-4 text-gray-400 transition-transform', cityOpen && 'rotate-180')} />}
              </button>
              {cityOpen && selectedState && (
                <div className="absolute z-50 w-full mt-1 max-h-52 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg">
                  {cities.map((city, index) => (
                    <button key={`${city.city}-${city.ward}-${index}`} type="button" onClick={() => handleCitySelect(city)}
                      className={cn('w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors', selectedCity?.display === city.display && 'bg-purple-50 dark:bg-purple-900/20 text-purple-600')}>
                      <div className="font-medium">{city.display}</div>
                      <div className="text-xs text-gray-400">{city.latitude.toFixed(4)}, {city.longitude.toFixed(4)}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Country</label>
              <input type="text" name="country" value={formData.country} readOnly
                className="w-full px-4 py-3 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-500 rounded-xl cursor-not-allowed" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Postal Code</label>
              <input type="text" name="postal_code" value={formData.postal_code} onChange={handleChange}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>
          </div>

          {selectedCity && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-100 dark:border-purple-800">
              <div className="flex items-center gap-2 text-sm text-purple-700 dark:text-purple-300">
                <MapPin className="w-4 h-4" />
                <span>Location: {selectedCity.display} • {selectedCity.latitude.toFixed(4)}, {selectedCity.longitude.toFixed(4)}</span>
              </div>
            </motion.div>
          )}

          <div className="flex gap-4">
            <button type="submit" className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors">Save Changes</button>
            <button type="button" onClick={() => setIsEditing(false)} className="px-8 py-3 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-semibold rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">Cancel</button>
          </div>
        </motion.form>
      ) : (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Contact Information</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-4"><Mail className="w-5 h-5 text-gray-400" /><div><p className="text-sm text-gray-500 dark:text-gray-400">Email</p><p className="text-gray-900 dark:text-white">{user?.email}</p></div></div>
            <div className="flex items-center gap-4"><Phone className="w-5 h-5 text-gray-400" /><div><p className="text-sm text-gray-500 dark:text-gray-400">Phone</p><p className="text-gray-900 dark:text-white">{user?.phone_number || 'Not provided'}</p></div></div>
            <div className="flex items-center gap-4"><MapPin className="w-5 h-5 text-gray-400" /><div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Address</p>
              <p className="text-gray-900 dark:text-white">
                {user?.address ? `${user.address}, ${user.city}, ${user.state}, ${user.country} ${user.postal_code}` : 'Not provided'}
              </p>
              {user?.latitude && user?.longitude && <p className="text-xs text-gray-400 mt-1">Coordinates: {user.latitude}, {user.longitude}</p>}
            </div></div>
          </div>
        </motion.div>
      )}

      {/* Payuee PIN Modal */}
      <PayueePinModal
        isOpen={showPinModal}
        onClose={() => setShowPinModal(false)}
        onPinSet={handlePinSet}
      />
    </div>
  );
}