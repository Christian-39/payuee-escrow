/**
 * Admin Dashboard
 */

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  DollarSign,
  ShoppingCart,
  Users,
  Package,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Wallet,
  Landmark,
  Copy,
  RefreshCw,
  Eye,
  EyeOff,
  AlertCircle,
  CreditCard,
} from 'lucide-react';
import api from '../../lib/api';
import type { DashboardStats } from '../../types';
import { toast } from 'sonner';

interface PayueeWalletData {
  success: boolean;
  wallet_balance?: number;
  currency?: string;
  wallet_funding_account?: {
    account_name: string;
    account_number: string;
    bank_name: string;
    bank_code: string;
  };
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [walletData, setWalletData] = useState<PayueeWalletData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showBalance, setShowBalance] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);

      const [statsRes, walletRes] = await Promise.allSettled([
        api.get('/admin/stats/'),
        api.get('/payments/admin/wallet/balance/'),
      ]);

      if (statsRes.status === 'fulfilled') {
        setStats(statsRes.value.data);
      }

      if (walletRes.status === 'fulfilled') {
        setWalletData(walletRes.value.data);
      }
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchDashboardData();
    setIsRefreshing(false);
    toast.success('Dashboard refreshed');
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
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

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 dark:text-gray-400">
          Failed to load dashboard data
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Welcome back! Here's what's happening with your store.
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span className="text-sm font-medium">Refresh</span>
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Sales Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-xl">
              <DollarSign className="w-6 h-6 text-green-600" />
            </div>
            <span className="flex items-center gap-1 text-sm text-green-600">
              <TrendingUp className="w-4 h-4" />
              +12%
            </span>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Total Sales</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            ${stats.sales.total.toFixed(2)}
          </p>
        </motion.div>

        {/* Orders Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-xl">
              <ShoppingCart className="w-6 h-6 text-blue-600" />
            </div>
            <span className="flex items-center gap-1 text-sm text-blue-600">
              <ArrowUpRight className="w-4 h-4" />
              {stats.orders.pending} pending
            </span>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Total Orders</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {stats.orders.total}
          </p>
        </motion.div>

        {/* Customers Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-xl">
              <Users className="w-6 h-6 text-purple-600" />
            </div>
            <span className="flex items-center gap-1 text-sm text-purple-600">
              <TrendingUp className="w-4 h-4" />
              +{stats.customers.new_last_30_days} new
            </span>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Customers</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {stats.customers.total}
          </p>
        </motion.div>

        {/* Products Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-xl">
              <Package className="w-6 h-6 text-orange-600" />
            </div>
            <span className="flex items-center gap-1 text-sm text-red-600">
              <ArrowDownRight className="w-4 h-4" />
              {stats.products.low_stock} low
            </span>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Products</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {stats.products.total}
          </p>
        </motion.div>
      </div>

      {/* Payuee Wallet Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800"
      >
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1920&q=80')] bg-cover bg-center opacity-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-purple-900/60 to-transparent" />

        <div className="relative p-8 lg:p-10">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-8">
            {/* Balance Side */}
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-3 bg-white/20 backdrop-blur-sm rounded-xl">
                  <Wallet className="w-6 h-6 text-white" />
                </div>
                <div>
                  <p className="text-purple-200 text-sm">Payuee Escrow Wallet</p>
                  <div className="flex items-center gap-3">
                    <h2 className="text-4xl lg:text-5xl font-bold text-white">
                      {showBalance
                        ? formatAmount(
                            walletData?.wallet_balance,
                            walletData?.currency
                          )
                        : '****'}
                    </h2>
                    <button
                      onClick={() => setShowBalance(!showBalance)}
                      className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
                    >
                      {showBalance ? (
                        <EyeOff className="w-4 h-4 text-white" />
                      ) : (
                        <Eye className="w-4 h-4 text-white" />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-4 h-4 text-green-300" />
                    <span className="text-purple-200 text-sm">Available</span>
                  </div>
                  <p className="text-xl font-semibold text-white">
                    {showBalance
                      ? formatAmount(
                          walletData?.wallet_balance,
                          walletData?.currency
                        )
                      : '****'}
                  </p>
                </div>
                <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <CreditCard className="w-4 h-4 text-blue-300" />
                    <span className="text-purple-200 text-sm">Currency</span>
                  </div>
                  <p className="text-xl font-semibold text-white">
                    {walletData?.currency || 'NGN'}
                  </p>
                </div>
                <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="w-4 h-4 text-yellow-300" />
                    <span className="text-purple-200 text-sm">Status</span>
                  </div>
                  <p className="text-xl font-semibold text-white">Active</p>
                </div>
              </div>
            </div>

            {/* Funding Account Side */}
            <div className="lg:w-96">
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Landmark className="w-5 h-5 text-purple-200" />
                  <h3 className="text-white font-semibold">Funding Account</h3>
                </div>

                {walletData?.wallet_funding_account ? (
                  <div className="space-y-3">
                    <div className="p-3 bg-white/10 rounded-xl">
                      <p className="text-xs text-purple-200 mb-1">Account Name</p>
                      <div className="flex items-center justify-between">
                        <p className="text-white font-medium text-sm">
                          {walletData.wallet_funding_account.account_name}
                        </p>
                        <button
                          onClick={() =>
                            copyToClipboard(
                              walletData.wallet_funding_account!.account_name,
                              'Account name'
                            )
                          }
                          className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                        >
                          <Copy className="w-3.5 h-3.5 text-purple-200" />
                        </button>
                      </div>
                    </div>

                    <div className="p-3 bg-white/10 rounded-xl">
                      <p className="text-xs text-purple-200 mb-1">Account Number</p>
                      <div className="flex items-center justify-between">
                        <p className="text-white font-bold text-lg font-mono tracking-wider">
                          {walletData.wallet_funding_account.account_number}
                        </p>
                        <button
                          onClick={() =>
                            copyToClipboard(
                              walletData.wallet_funding_account!.account_number,
                              'Account number'
                            )
                          }
                          className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                        >
                          <Copy className="w-3.5 h-3.5 text-purple-200" />
                        </button>
                      </div>
                    </div>

                    <div className="p-3 bg-white/10 rounded-xl">
                      <p className="text-xs text-purple-200 mb-1">Bank</p>
                      <p className="text-white font-medium text-sm">
                        {walletData.wallet_funding_account.bank_name}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6">
                    <Landmark className="w-10 h-10 text-purple-300 mx-auto mb-2" />
                    <p className="text-purple-200 text-sm">
                      No funding account available
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Recent Orders & Low Stock */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Orders */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Recent Orders
          </h3>
          <div className="space-y-4">
            <p className="text-gray-500 dark:text-gray-400 text-center py-8">
              Recent orders will appear here
            </p>
          </div>
        </div>

        {/* Inventory Alert */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Inventory Alerts
          </h3>
          <div className="space-y-4">
            {stats.products.low_stock > 0 ? (
              <div className="flex items-center gap-3 p-4 bg-orange-50 dark:bg-orange-900/20 rounded-xl">
                <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                  <Package className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {stats.products.low_stock} products low in stock
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Review and restock items
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                No inventory alerts
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}