/**
 * Order Confirmation Page — Updated for Payuee Escrow Integration
 * 
 * Shows Payuee order IDs, escrow status, and wallet funding info for ON_HOLD orders.
 */

import { useEffect, useState } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle, Package, Home, ShoppingBag, AlertTriangle, Clock, Wallet, Copy, Check } from 'lucide-react';
import api from '../lib/api';
import type { Order } from '../types';
import { toast } from 'sonner';
import { formatPrice } from '../lib/utils';

export default function OrderConfirmationPage() {
  const { orderNumber } = useParams<{ orderNumber: string }>();
  const location = useLocation();
  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  // Get state passed from checkout (e.g., ON_HOLD status)
  const checkoutStatus = location.state?.status;
  const walletFundingRequired = location.state?.wallet_funding_required;

  useEffect(() => {
    if (orderNumber) {
      fetchOrder();
    }
  }, [orderNumber]);

  const fetchOrder = async () => {
    try {
      const response = await api.get(`/orders/${orderNumber}/`);
      setOrder(response.data);
    } catch (error) {
      toast.error('Failed to load order');
    } finally {
      setIsLoading(false);
    }
  };

  const copyOrderNumber = () => {
    if (order?.order_number) {
      navigator.clipboard.writeText(order.order_number);
      setCopied(true);
      toast.success('Order number copied');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isOnHold = order?.status === 'on_hold' || checkoutStatus === 'ON_HOLD';
  const isPaymentFailed = order?.status === 'payment_failed';
  const isSuccess = !isOnHold && !isPaymentFailed;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-12 h-12 border-4 border-purple-600/30 border-t-purple-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto text-center py-12">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="space-y-8"
      >
        {/* Status Icon */}
        <div className="w-24 h-24 rounded-full flex items-center justify-center mx-auto"
          style={{
            backgroundColor: isOnHold ? '#fff7ed' : isPaymentFailed ? '#fef2f2' : '#dcfce7'
          }}
        >
          {isOnHold ? (
            <Clock className="w-12 h-12 text-orange-600" />
          ) : isPaymentFailed ? (
            <AlertTriangle className="w-12 h-12 text-red-600" />
          ) : (
            <CheckCircle className="w-12 h-12 text-green-600" />
          )}
        </div>

        {/* Message */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            {isOnHold ? 'Order On Hold' :
             isPaymentFailed ? 'Payment Failed' :
             'Order Confirmed!'}
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            {isOnHold 
              ? 'Your order is pending wallet funding. Please fund your Payuee wallet within 24 hours.'
              : isPaymentFailed
              ? 'There was an issue processing your payment. Your order has been saved locally.'
              : 'Thank you for your purchase. Your order has been received and secured in escrow.'}
          </p>
        </div>

        {/* Order Details */}
        {order && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700 text-left"
          >
            {/* Order Number & Total */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Order Number
                </p>
                <div className="flex items-center gap-2">
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {order.order_number}
                  </p>
                  <button 
                    onClick={copyOrderNumber}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                    title="Copy order number"
                  >
                    {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4 text-gray-400" />}
                  </button>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Total Amount
                </p>
                <p className="text-2xl font-bold text-purple-600">
                  {formatPrice(order.total)}
                </p>
              </div>
            </div>

            {/* Payuee Order IDs */}
            {order.payuee_order_ids && order.payuee_order_ids.length > 0 && (
              <div className="mb-4 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-100 dark:border-purple-800">
                <p className="text-sm font-medium text-purple-800 dark:text-purple-300 mb-1">
                  Payuee Order {order.payuee_order_ids.length > 1 ? 'IDs' : 'ID'}
                </p>
                <p className="text-sm text-purple-700 dark:text-purple-400 font-mono">
                  {order.payuee_order_ids.join(', ')}
                </p>
              </div>
            )}

            {/* Escrow Status */}
            <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800">
              <div className="flex items-center gap-2">
                <Wallet className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium text-blue-800 dark:text-blue-300">
                  Escrow Status: {order.payuee_escrow_status 
                    ? order.payuee_escrow_status.charAt(0).toUpperCase() + order.payuee_escrow_status.slice(1)
                    : 'Pending'}
                </span>
              </div>
            </div>

            {/* ON_HOLD Alert */}
            {isOnHold && (
              <div className="mb-4 p-4 bg-orange-50 dark:bg-orange-900/20 rounded-xl border border-orange-200 dark:border-orange-800">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-orange-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-orange-800 dark:text-orange-300">
                      Wallet Funding Required
                    </p>
                    <p className="text-sm text-orange-700 dark:text-orange-400 mt-1">
                      Your Payuee wallet balance is insufficient. Please fund your wallet within <strong>24 hours</strong> to avoid automatic cancellation.
                    </p>
                    <Link
                      to="/wallet"
                      className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 transition-colors"
                    >
                      <Wallet className="w-4 h-4" />
                      Fund Wallet
                    </Link>
                  </div>
                </div>
              </div>
            )}

            {/* Payment Failed Alert */}
            {isPaymentFailed && order.payuee_error && (
              <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-800 dark:text-red-300">
                      Payment Error
                    </p>
                    <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                      {order.payuee_error}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* What's Next */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                What's Next?
              </p>
              <ul className="space-y-2 text-gray-600 dark:text-gray-400">
                <li className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-purple-600" />
                  {isOnHold 
                    ? 'Fund your wallet to proceed with fulfillment'
                    : 'You will receive an email confirmation shortly'}
                </li>
                <li className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-purple-600" />
                  {isOnHold
                    ? 'Order will be automatically cancelled after 24 hours if not funded'
                    : "We'll notify you when your order ships"}
                </li>
                <li className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-purple-600" />
                  Track your order status in your account
                </li>
              </ul>
            </div>
          </motion.div>
        )}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            to="/orders"
            className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors"
          >
            <Package className="w-5 h-5" />
            View Orders
          </Link>
          {isOnHold && (
            <Link
              to="/wallet"
              className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-orange-600 text-white font-semibold rounded-xl hover:bg-orange-700 transition-colors"
            >
              <Wallet className="w-5 h-5" />
              Fund Wallet
            </Link>
          )}
          <Link
            to="/products"
            className="inline-flex items-center justify-center gap-2 px-8 py-3.5 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-semibold rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <ShoppingBag className="w-5 h-5" />
            Continue Shopping
          </Link>
        </div>

        <Link
          to="/"
          className="inline-flex items-center gap-2 text-purple-600 hover:text-purple-700 font-medium"
        >
          <Home className="w-5 h-5" />
          Back to Home
        </Link>
      </motion.div>
    </div>
  );
}