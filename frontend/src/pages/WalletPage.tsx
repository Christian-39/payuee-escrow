/**
 * Wallet Page
 * Displays Payuee wallet balance, funding details, and transaction history.
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Wallet,
  ArrowUpRight,
  ArrowDownLeft,
  Copy,
  RefreshCw,
  CreditCard,
  Landmark,
  Clock,
  AlertCircle,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Eye,
  EyeOff,
  Banknote,
  CheckCircle2,
  X,
  Info,
  Building2,
  Mail,
  ExternalLink,
  MessageCircle,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import api from '../lib/api';
import { toast } from 'sonner';

interface WalletBalance {
  status: string;
  wallet_balance: number;
  currency: string;
}

interface FundingAccount {
  account_name: string;
  account_number: string;
  bank_name: string;
  bank_code: string;
}

interface WalletFundingDetails {
  wallet_funding_account: FundingAccount;
  wallet_balance: number;
}

interface WalletTransaction {
  id: string;
  type: 'credit' | 'debit';
  amount: number;
  description: string;
  status: 'completed' | 'pending' | 'failed';
  created_at: string;
  reference?: string;
}

interface Transaction {
  id: string;
  transaction_type: string;
  amount: number;
  status: string;
  created_at: string;
  description: string;
  reference: string;
}

interface FundingError {
  error: string;
  detail?: string;
  status_code?: number;
}

export default function WalletPage() {
  const { user } = useAuth();
  const [balance, setBalance] = useState<WalletBalance | null>(null);
  const [fundingDetails, setFundingDetails] = useState<WalletFundingDetails | null>(null);
  const [fundingError, setFundingError] = useState<FundingError | null>(null);
  const [walletTransactions, setWalletTransactions] = useState<WalletTransaction[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showBalance, setShowBalance] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions'>('overview');
  const [showFundingModal, setShowFundingModal] = useState(false);

  useEffect(() => {
    fetchWalletData();
  }, []);

  const fetchWalletData = async () => {
    try {
      setIsLoading(true);
      setFundingError(null);

      const [balanceRes, fundingRes, walletTxRes, txRes] = await Promise.allSettled([
        api.get('/payments/wallet/balance/'),
        api.get('/payments/wallet/funding-details/'),
        api.get('/payments/wallet-transactions/'),
        api.get('/payments/transactions/'),
      ]);

      if (balanceRes.status === 'fulfilled') {
        const balData = balanceRes.value.data;
        if (balData.success) {
          setBalance({
            status: balData.status || 'success',
            wallet_balance: balData.wallet_balance || 0,
            currency: balData.currency || 'NGN',
          });
        }
      }

      if (fundingRes.status === 'fulfilled') {
        const fundData = fundingRes.value.data;
        if (fundData.success && fundData.wallet_funding_account) {
          setFundingDetails({
            wallet_funding_account: fundData.wallet_funding_account,
            wallet_balance: fundData.wallet_balance || 0,
          });
          setFundingError(null);
        } else if (!fundData.success) {
          setFundingError({
            error: fundData.error || 'Failed to load funding details',
            detail: fundData.detail,
            status_code: fundData.status_code,
          });
        }
      } else {
        // Request failed entirely
        setFundingError({
          error: 'Unable to connect to Payuee funding service',
        });
      }

      if (walletTxRes.status === 'fulfilled') {
        setWalletTransactions(walletTxRes.value.data.results || walletTxRes.value.data || []);
      }

      if (txRes.status === 'fulfilled') {
        setTransactions(txRes.value.data.results || txRes.value.data || []);
      }
    } catch (error) {
      toast.error('Failed to load wallet data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchWalletData();
    setIsRefreshing(false);
    toast.success('Wallet data refreshed');
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-NG', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'success':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'pending':
      case 'on_hold':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'failed':
      case 'cancelled':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  const getTransactionIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'credit':
      case 'deposit':
      case 'refund':
        return <ArrowDownLeft className="w-5 h-5 text-green-600 dark:text-green-400" />;
      case 'debit':
      case 'withdrawal':
      case 'payment':
        return <ArrowUpRight className="w-5 h-5 text-red-600 dark:text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500 dark:text-gray-400" />;
    }
  };

  const account = fundingDetails?.wallet_funding_account;
  const isFundingDisabled = fundingError?.status_code === 405;

  if (!user) {
    return (
      <div className="text-center py-16">
        <Wallet className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500 dark:text-gray-400">
          Please login to view your wallet
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            My Wallet
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Manage your Payuee escrow wallet
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
      </motion.div>

      {/* Balance Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800"
      >
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1920&q=80')] bg-cover bg-center opacity-10" />
        <div className="absolute inset-0 bg-gradient-to-r from-purple-900/60 to-transparent" />

        <div className="relative p-8 lg:p-10">
          <div className="flex items-start justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-white/20 backdrop-blur-sm rounded-xl">
                <Wallet className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-purple-200 text-sm">Available Balance</p>
                <div className="flex items-center gap-3">
                  <h2 className="text-4xl lg:text-5xl font-bold text-white">
                    {isLoading ? (
                      <span className="inline-block w-40 h-10 bg-white/20 rounded animate-pulse" />
                    ) : showBalance ? (
                      formatAmount(balance?.wallet_balance, balance?.currency)
                    ) : (
                      '****'
                    )}
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
            <div className="hidden sm:flex flex-col items-end gap-2">
              <span className="px-3 py-1.5 bg-green-400/20 text-green-300 text-sm font-medium rounded-full backdrop-blur-sm">
                Active
              </span>
              {!isFundingDisabled && (
                <button
                  onClick={() => setShowFundingModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-white/20 backdrop-blur-sm rounded-xl text-white text-sm font-medium hover:bg-white/30 transition-colors"
                >
                  <Banknote className="w-4 h-4" />
                  Fund Wallet
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-green-300" />
                <span className="text-purple-200 text-sm">Total Credited</span>
              </div>
              <p className="text-xl font-semibold text-white">
                {isLoading ? '—' : formatAmount(
                  walletTransactions
                    .filter((t) => t.type === 'credit')
                    .reduce((sum, t) => sum + t.amount, 0),
                  balance?.currency
                )}
              </p>
            </div>
            <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown className="w-4 h-4 text-red-300" />
                <span className="text-purple-200 text-sm">Total Debited</span>
              </div>
              <p className="text-xl font-semibold text-white">
                {isLoading ? '—' : formatAmount(
                  walletTransactions
                    .filter((t) => t.type === 'debit')
                    .reduce((sum, t) => sum + t.amount, 0),
                  balance?.currency
                )}
              </p>
            </div>
            <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-yellow-300" />
                <span className="text-purple-200 text-sm">Pending</span>
              </div>
              <p className="text-xl font-semibold text-white">
                {isLoading ? '—' : formatAmount(
                  walletTransactions
                    .filter((t) => t.status === 'pending')
                    .reduce((sum, t) => sum + t.amount, 0),
                  balance?.currency
                )}
              </p>
            </div>
          </div>

          {/* Mobile Fund Button */}
          {!isFundingDisabled && (
            <div className="sm:hidden mt-4">
              <button
                onClick={() => setShowFundingModal(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white/20 backdrop-blur-sm rounded-xl text-white text-sm font-medium hover:bg-white/30 transition-colors"
              >
                <Banknote className="w-4 h-4" />
                Fund Wallet
              </button>
            </div>
          )}
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'overview'
              ? 'bg-white dark:bg-gray-700 text-purple-600 dark:text-purple-400 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('transactions')}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'transactions'
              ? 'bg-white dark:bg-gray-700 text-purple-600 dark:text-purple-400 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          Transactions
        </button>
      </div>

      {activeTab === 'overview' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Funding Account Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-xl">
                <Landmark className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Funding Account
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Transfer funds to this account
                </p>
              </div>
            </div>

            {isLoading ? (
              <div className="space-y-4">
                {[...Array(4)].map((_, i) => (
                  <div
                    key={i}
                    className="h-14 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse"
                  />
                ))}
              </div>
            ) : isFundingDisabled ? (
              /* Payuee funding not enabled */
              <div className="text-center py-8 space-y-4">
                <div className="w-16 h-16 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center mx-auto">
                  <AlertCircle className="w-8 h-8 text-orange-600 dark:text-orange-400" />
                </div>
                <div>
                  <p className="text-gray-900 dark:text-white font-medium mb-1">
                    Wallet Funding Not Available
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                    {fundingError?.error || 'Virtual account funding is not enabled for your Payuee account.'}
                  </p>
                </div>
                <div className="flex flex-col gap-2 max-w-xs mx-auto">
                  <a
                    href="mailto:support@payuee.com"
                    className="flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors text-sm font-medium"
                  >
                    <Mail className="w-4 h-4" />
                    Contact Payuee Support
                  </a>
                  <button
                    onClick={() => {
                      window.open('https://payuee.com', '_blank');
                    }}
                    className="flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-sm font-medium"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Visit Payuee Website
                  </button>
                </div>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Ask them to enable "virtual account wallet funding" for your API credentials.
                </p>
              </div>
            ) : account ? (
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                    Account Name
                  </p>
                  <div className="flex items-center justify-between">
                    <p className="text-gray-900 dark:text-white font-medium">
                      {account.account_name}
                    </p>
                    <button
                      onClick={() => copyToClipboard(account.account_name, 'Account name')}
                      className="p-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                    >
                      <Copy className="w-4 h-4 text-gray-500" />
                    </button>
                  </div>
                </div>

                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                    Account Number
                  </p>
                  <div className="flex items-center justify-between">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white font-mono tracking-wider">
                      {account.account_number}
                    </p>
                    <button
                      onClick={() => copyToClipboard(account.account_number, 'Account number')}
                      className="p-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                    >
                      <Copy className="w-4 h-4 text-gray-500" />
                    </button>
                  </div>
                </div>

                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                    Bank Name
                  </p>
                  <div className="flex items-center justify-between">
                    <p className="text-gray-900 dark:text-white font-medium">
                      {account.bank_name}
                    </p>
                    <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                      Code: {account.bank_code}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => setShowFundingModal(true)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors font-medium"
                >
                  <Info className="w-4 h-4" />
                  How to Fund Your Wallet
                </button>
              </div>
            ) : (
              <div className="text-center py-8">
                <Banknote className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-gray-400">
                  No funding account available
                </p>
              </div>
            )}
          </motion.div>

          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-xl">
                  <CreditCard className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Recent Activity
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Latest wallet movements
                  </p>
                </div>
              </div>
              <button
                onClick={() => setActiveTab('transactions')}
                className="flex items-center gap-1 text-sm text-purple-600 hover:text-purple-700 font-medium"
              >
                View All
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {isLoading ? (
              <div className="space-y-4">
                {[...Array(4)].map((_, i) => (
                  <div
                    key={i}
                    className="h-16 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse"
                  />
                ))}
              </div>
            ) : walletTransactions.length > 0 ? (
              <div className="space-y-3">
                {walletTransactions.slice(0, 5).map((tx, index) => (
                  <motion.div
                    key={tx.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    <div
                      className={`p-2.5 rounded-xl ${
                        tx.type === 'credit'
                          ? 'bg-green-100 dark:bg-green-900/30'
                          : 'bg-red-100 dark:bg-red-900/30'
                      }`}
                    >
                      {getTransactionIcon(tx.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {tx.description}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatDate(tx.created_at)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className={`text-sm font-semibold ${
                          tx.type === 'credit'
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {tx.type === 'credit' ? '+' : '-'}
                        {formatAmount(tx.amount, balance?.currency)}
                      </p>
                      <span
                        className={`inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full ${getStatusColor(
                          tx.status
                        )}`}
                      >
                        {tx.status}
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-gray-400">
                  No recent activity
                </p>
              </div>
            )}
          </motion.div>
        </div>
      ) : (
        /* Transactions Tab */
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden"
        >
          <div className="p-6 border-b border-gray-100 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              All Transactions
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Complete history of your wallet and order transactions
            </p>
          </div>

          {isLoading ? (
            <div className="p-6 space-y-4">
              {[...Array(6)].map((_, i) => (
                <div
                  key={i}
                  className="h-16 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse"
                />
              ))}
            </div>
          ) : transactions.length > 0 ? (
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {transactions.map((tx, index) => (
                <motion.div
                  key={tx.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.03 }}
                  className="flex items-center gap-4 p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div
                    className={`p-2.5 rounded-xl ${
                      tx.transaction_type?.toLowerCase().includes('credit') ||
                      tx.transaction_type?.toLowerCase().includes('refund')
                        ? 'bg-green-100 dark:bg-green-900/30'
                        : 'bg-red-100 dark:bg-red-900/30'
                    }`}
                  >
                    {getTransactionIcon(tx.transaction_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {tx.description}
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatDate(tx.created_at)}
                      </p>
                      <span className="text-gray-300 dark:text-gray-600">•</span>
                      <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                        {tx.reference}
                      </p>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p
                      className={`text-sm font-semibold ${
                        tx.transaction_type?.toLowerCase().includes('credit') ||
                        tx.transaction_type?.toLowerCase().includes('refund')
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {tx.transaction_type?.toLowerCase().includes('credit') ||
                      tx.transaction_type?.toLowerCase().includes('refund')
                        ? '+'
                        : '-'}
                      {formatAmount(tx.amount, balance?.currency)}
                    </p>
                    <span
                      className={`inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full ${getStatusColor(
                        tx.status
                      )}`}
                    >
                      {tx.status}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <CreditCard className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">
                No transactions found
              </p>
            </div>
          )}
        </motion.div>
      )}

      {/* ─── FUNDING MODAL ─── */}
      <AnimatePresence>
        {showFundingModal && account && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowFundingModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-lg bg-white dark:bg-gray-800 rounded-3xl shadow-2xl overflow-hidden"
            >
              {/* Modal Header */}
              <div className="relative p-6 bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800">
                <button
                  onClick={() => setShowFundingModal(false)}
                  className="absolute top-4 right-4 p-2 bg-white/20 rounded-lg hover:bg-white/30 transition-colors"
                >
                  <X className="w-5 h-5 text-white" />
                </button>
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-white/20 rounded-xl">
                    <Banknote className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white">Fund Your Wallet</h2>
                    <p className="text-purple-200 text-sm">
                      Transfer funds to your dedicated virtual account
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-6 space-y-6">
                {/* Account Details */}
                <div className="space-y-3">
                  <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl border border-gray-100 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Account Name</p>
                    <div className="flex items-center justify-between">
                      <p className="text-gray-900 dark:text-white font-medium text-sm">
                        {account.account_name}
                      </p>
                      <button
                        onClick={() => copyToClipboard(account.account_name, 'Account name')}
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                      >
                        <Copy className="w-3.5 h-3.5 text-gray-500" />
                      </button>
                    </div>
                  </div>

                  <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl border border-gray-100 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Account Number</p>
                    <div className="flex items-center justify-between">
                      <p className="text-2xl font-bold text-gray-900 dark:text-white font-mono tracking-wider">
                        {account.account_number}
                      </p>
                      <button
                        onClick={() => copyToClipboard(account.account_number, 'Account number')}
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                      >
                        <Copy className="w-3.5 h-3.5 text-gray-500" />
                      </button>
                    </div>
                  </div>

                  <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl border border-gray-100 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Bank</p>
                    <p className="text-gray-900 dark:text-white font-medium text-sm">
                      {account.bank_name}
                    </p>
                  </div>
                </div>

                {/* Steps */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                    How to fund:
                  </h3>

                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center">
                        <span className="text-sm font-bold text-purple-600 dark:text-purple-400">1</span>
                      </div>
                      <div className="w-0.5 h-full bg-purple-100 dark:bg-purple-900/30 my-1" />
                    </div>
                    <div className="pb-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Building2 className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Bank Transfer
                        </p>
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Log into your business bank app or internet banking and initiate a transfer to the account details above.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center">
                        <span className="text-sm font-bold text-purple-600 dark:text-purple-400">2</span>
                      </div>
                      <div className="w-0.5 h-full bg-purple-100 dark:bg-purple-900/30 my-1" />
                    </div>
                    <div className="pb-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Clock className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Wait for Confirmation
                        </p>
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Transfers typically take 1–5 minutes to reflect. Payuee auto-detects and credits your wallet.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                        <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Mail className="w-4 h-4 text-green-600 dark:text-green-400" />
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Webhook Notification
                        </p>
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        You'll receive a webhook event when the funds are credited. Refresh your wallet to see the updated balance.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Important Notice */}
                <div className="flex items-start gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl">
                  <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-yellow-800 dark:text-yellow-300 font-medium">
                      Important
                    </p>
                    <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                      This is a dedicated virtual account assigned to your business. 
                      Always transfer from your registered business bank account. 
                      Third-party transfers may be rejected or flagged for review.
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => {
                    setShowFundingModal(false);
                    handleRefresh();
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors font-medium"
                >
                  <RefreshCw className="w-4 h-4" />
                  Check Balance Now
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}