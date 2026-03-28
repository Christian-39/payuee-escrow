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
} from 'lucide-react';
import api from '../../lib/api';
import type { DashboardStats } from '../../types';
import { toast } from 'sonner';

const statCards = [
  { key: 'sales', label: 'Total Sales', icon: DollarSign, color: 'bg-green-500' },
  { key: 'orders', label: 'Total Orders', icon: ShoppingCart, color: 'bg-blue-500' },
  { key: 'customers', label: 'Customers', icon: Users, color: 'bg-purple-500' },
  { key: 'products', label: 'Products', icon: Package, color: 'bg-orange-500' },
];

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await api.get('/admin/stats/');
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard stats');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Welcome back! Here's what's happening with your store.
        </p>
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

      {/* Recent Orders & Low Stock */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Orders */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Recent Orders
          </h3>
          <div className="space-y-4">
            {/* Placeholder for recent orders */}
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
