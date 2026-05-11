/**
 * Admin Wallet Page
 * Full wallet management for administrators — balance, funding details, transactions.
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Wallet,
  ArrowUpRight,
  ArrowDownLeft,
  Copy,
  RefreshCw,
  Landmark,
  Clock,
  AlertCircle,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Eye,
  EyeOff,
  Banknote,
  CreditCard,
  Filter,
  Download,
  Search,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-react';
import api from '../../lib/api';
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
  user?: {
    id: string;
    full_name: string;
    email: string;
  };
}

type TransactionFilter = 'all' | 'credit' | 'debit' | 'pending';

export default function AdminWalletPage() {
  const [balance, setBalance] = useState<WalletBalance | null>(null);
  const [fundingDetails, setFundingDetails] = useState<WalletFundingDetails | null>(null);
  const [walletTransactions, setWalletTransactions] = useState<WalletTransaction[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showBalance, setShowBalance] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions'>('overview');
  const [filter, setFilter] = useState<TransactionFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchWalletData();
  }, []);

  const fetchWalletData = async () => {
    try {
      setIsLoading(true);

      const [balanceRes, fundingRes, walletTxRes, txRes] = await Promise.allSettled([
        api.get('/payments/admin/wallet/balance/'),
        api.get('/payments/admin/wallet/funding-details/'),
        api.get('/payments/admin/wallet-transactions/'),
        api.get('/payments/admin/transactions/'),
      ]);

      if (balanceRes.status === 'fulfilled' && balanceRes.value.data.success) {
        setBalance(balanceRes.value.data);
      }

      if (fundingRes.status === 'fulfilled' && fundingRes.value.data.success) {
        setFundingDetails(fundingRes.value.data);
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

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />;
      case 'failed':
      case 'cancelled':
        return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />;
      case 'pending':
        return <Loader2 className="w-4 h-4 text-yellow-600 dark:text-yellow-400 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
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

  const filteredTransactions = transactions.filter((tx) => {
    const matchesFilter =
      filter === 'all'
        ? true
        : filter === 'pending'
        ? tx.status.toLowerCase() === 'pending'
        : tx.transaction_type?.toLowerCase().includes(filter);

    const matchesSearch =
      searchQuery === ''
        ? true
        : tx.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          tx.reference?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          tx.user?.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          tx.user?.email?.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  const totalCredits = walletTransactions
    .filter((t) => t.type === 'credit')
    .reduce((sum, t) => sum + t.amount, 0);

  const totalDebits = walletTransactions
    .filter((t) => t.type === 'debit')
    .reduce((sum, t) => sum + t.amount, 0);

  const pendingAmount = walletTransactions
    .filter((t) => t.status === 'pending')
    .reduce((sum, t) => sum + t.amount, 0);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Wallet Management
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Manage Payuee escrow wallet and monitor all transactions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="text-sm font-medium">Refresh</span>
          </button>
          <button
            onClick={() => toast.info('Export feature coming soon')}
            className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors"
          >
            <Download className="w-4 h-4" />
            <span className="text-sm font-medium">Export</span>
          </button>
        </div>
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
                <p className="text-purple-200 text-sm">Payuee Escrow Balance</p>
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
            <div className="hidden sm:block">
              <span className="px-3 py-1.5 bg-green-400/20 text-green-300 text-sm font-medium rounded-full backdrop-blur-sm">
                Active
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-green-300" />
                <span className="text-purple-200 text-sm">Total Credited</span>
              </div>
              <p className="text-xl font-semibold text-white">
                {isLoading ? '—' : formatAmount(totalCredits, balance?.currency)}
              </p>
            </div>
            <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown className="w-4 h-4 text-red-300" />
                <span className="text-purple-200 text-sm">Total Debited</span>
              </div>
              <p className="text-xl font-semibold text-white">
                {isLoading ? '—' : formatAmount(totalDebits, balance?.currency)}
              </p>
            </div>
            <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-yellow-300" />
                <span className="text-purple-200 text-sm">Pending</span>
              </div>
              <p className="text-xl font-semibold text-white">
                {isLoading ? '—' : formatAmount(pendingAmount, balance?.currency)}
              </p>
            </div>
            <div className="p-4 bg-white/10 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <CreditCard className="w-4 h-4 text-blue-300" />
                <span className="text-purple-200 text-sm">Currency</span>
              </div>
              <p className="text-xl font-semibold text-white">
                {balance?.currency || 'NGN'}
              </p>
            </div>
          </div>
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
          All Transactions
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
                  Transfer funds to this dedicated virtual account
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
            ) : fundingDetails?.wallet_funding_account ? (
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                    Account Name
                  </p>
                  <div className="flex items-center justify-between">
                    <p className="text-gray-900 dark:text-white font-medium">
                      {fundingDetails.wallet_funding_account.account_name}
                    </p>
                    <button
                      onClick={() =>
                        copyToClipboard(
                          fundingDetails.wallet_funding_account.account_name,
                          'Account name'
                        )
                      }
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
                      {fundingDetails.wallet_funding_account.account_number}
                    </p>
                    <button
                      onClick={() =>
                        copyToClipboard(
                          fundingDetails.wallet_funding_account.account_number,
                          'Account number'
                        )
                      }
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
                      {fundingDetails.wallet_funding_account.bank_name}
                    </p>
                    <span className="text-xs text-gray-500 dark:text-gray-400 font-mono bg-gray-100 dark:bg-gray-600 px-2 py-1 rounded">
                      Code: {fundingDetails.wallet_funding_account.bank_code}
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl">
                  <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-yellow-800 dark:text-yellow-300 font-medium">
                      Important
                    </p>
                    <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                      Transfer funds to this account from your business bank.
                      Your wallet will be automatically credited once confirmed.
                      A webhook notification will be sent upon successful funding.
                    </p>
                  </div>
                </div>
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
          className="space-y-6"
        >
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by description, reference, or user..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div className="flex items-center gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl">
              {(['all', 'credit', 'debit', 'pending'] as TransactionFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize ${
                    filter === f
                      ? 'bg-white dark:bg-gray-700 text-purple-600 dark:text-purple-400 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Transactions Table */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100 dark:border-gray-700">
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Transaction
                    </th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      User
                    </th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Reference
                    </th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="text-right px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="text-center px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {isLoading ? (
                    [...Array(5)].map((_, i) => (
                      <tr key={i}>
                        <td colSpan={6} className="px-6 py-4">
                          <div className="h-12 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />
                        </td>
                      </tr>
                    ))
                  ) : filteredTransactions.length > 0 ? (
                    filteredTransactions.map((tx, index) => (
                      <motion.tr
                        key={tx.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: index * 0.03 }}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div
                              className={`p-2 rounded-lg ${
                                tx.transaction_type?.toLowerCase().includes('credit') ||
                                tx.transaction_type?.toLowerCase().includes('refund')
                                  ? 'bg-green-100 dark:bg-green-900/30'
                                  : 'bg-red-100 dark:bg-red-900/30'
                              }`}
                            >
                              {getTransactionIcon(tx.transaction_type)}
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900 dark:text-white">
                                {tx.description}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                                {tx.transaction_type}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          {tx.user ? (
                            <div>
                              <p className="text-sm text-gray-900 dark:text-white">
                                {tx.user.full_name}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                {tx.user.email}
                              </p>
                            </div>
                          ) : (
                            <span className="text-sm text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                            {tx.reference}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {formatDate(tx.created_at)}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
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
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span
                            className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full ${getStatusColor(
                              tx.status
                            )}`}
                          >
                            {getStatusIcon(tx.status)}
                            {tx.status}
                          </span>
                        </td>
                      </motion.tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-6 py-16 text-center">
                        <CreditCard className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500 dark:text-gray-400">
                          No transactions found
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}