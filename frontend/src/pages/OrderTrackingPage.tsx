/**
 * Order Tracking Page — Updated for Payuee Escrow Integration
 * 
 * Shows escrow-specific statuses, QR verification info, and Payuee order details.
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Package, Truck, CheckCircle, Clock, ChevronLeft, Wallet, AlertTriangle, QrCode, Shield, XCircle, Flag } from 'lucide-react';
import api from '../lib/api';
import type { Order } from '../types';
import { toast } from 'sonner';
import { formatDate, formatPrice } from '../lib/utils';

// Standard order flow steps
const statusSteps = [
  { key: 'pending', label: 'Order Placed', icon: Clock },
  { key: 'confirmed', label: 'Confirmed', icon: CheckCircle },
  { key: 'processing', label: 'Processing', icon: Package },
  { key: 'shipped', label: 'Shipped', icon: Truck },
  { key: 'delivered', label: 'Delivered', icon: CheckCircle },
];

// Payuee escrow lifecycle states (from docs)
const escrowStates = [
  { key: 'created', label: 'Created', desc: 'Order received by Payuee' },
  { key: 'escrow_locked', label: 'Escrow Locked', desc: 'Funds secured in escrow' },
  { key: 'confirmed', label: 'Confirmed', desc: 'Vendor accepted order' },
  { key: 'delivered', label: 'Delivered', desc: 'Delivery verified' },
  { key: 'released', label: 'Released', desc: 'Funds released to vendor' },
];

export default function OrderTrackingPage() {
  const { orderNumber } = useParams<{ orderNumber: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [pin, setPin] = useState('');
  const [reportNote, setReportNote] = useState('');
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);

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

  const handleCancelOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(pin)) {
      toast.error('Enter your 6-digit Payuee PIN');
      return;
    }
    setIsSubmittingAction(true);
    try {
      const response = await api.post(`/orders/${orderNumber}/cancel/`, {
        trans_code: pin,
        report_note: reportNote,
      });
      setOrder(response.data.order);
      toast.success('Order cancelled');
      setShowCancelModal(false);
      setPin('');
      setReportNote('');
    } catch (error: any) {
      const data = error.response?.data;
      toast.error(data?.trans_code || data?.error || 'Failed to cancel order');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleReportOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportNote.trim()) {
      toast.error('Please describe the issue');
      return;
    }
    setIsSubmittingAction(true);
    try {
      await api.post(`/orders/${orderNumber}/report/`, { report_note: reportNote });
      toast.success('Report submitted - our team will review it shortly');
      setShowReportModal(false);
      setReportNote('');
    } catch (error: any) {
      const data = error.response?.data;
      toast.error(data?.report_note || data?.error || 'Failed to submit report');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const isCancellable = order && ['pending', 'confirmed', 'processing'].includes(order.status);
  const isReportable = order && !['cancelled', 'refunded'].includes(order.status);

  const getCurrentStep = () => {
    if (!order) return 0;
    const stepIndex = statusSteps.findIndex((s) => s.key === order.status);
    return stepIndex >= 0 ? stepIndex : 0;
  };

  const getEscrowStepIndex = () => {
    if (!order?.payuee_escrow_status) return 0;
    const idx = escrowStates.findIndex(s => s.key === order.payuee_escrow_status);
    return idx >= 0 ? idx : 0;
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="text-center py-16">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Order Not Found
        </h2>
        <Link
          to="/orders"
          className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
          Back to Orders
        </Link>
      </div>
    );
  }

  const currentStep = getCurrentStep();
  const escrowStep = getEscrowStepIndex();
  const isOnHold = order.status === 'on_hold';
  const isPaymentFailed = order.status === 'payment_failed';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/orders"
          className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ChevronLeft className="w-6 h-6" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Order {order.order_number}
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Placed on {formatDate(order.created_at)}
          </p>
        </div>
        <div className="ml-auto flex gap-2">
          {isCancellable && (
            <button
              onClick={() => { setReportNote(''); setPin(''); setShowCancelModal(true); }}
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              <XCircle className="w-4 h-4" /> Cancel Order
            </button>
          )}
          {isReportable && (
            <button
              onClick={() => { setReportNote(''); setShowReportModal(true); }}
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <Flag className="w-4 h-4" /> Report Issue
            </button>
          )}
        </div>
      </div>

      {/* ON_HOLD Alert Banner */}
      {isOnHold && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-2xl p-6"
        >
          <div className="flex items-start gap-4">
            <div className="p-2 bg-orange-100 dark:bg-orange-800 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-orange-800 dark:text-orange-300">
                Wallet Funding Required
              </h3>
              <p className="text-sm text-orange-700 dark:text-orange-400 mt-1">
                Your order is on hold because your Payuee wallet has insufficient balance. 
                Please fund your wallet within <strong>24 hours</strong> to avoid automatic cancellation.
              </p>
              <Link
                to="/wallet"
                className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 transition-colors"
              >
                <Wallet className="w-4 h-4" />
                Fund Wallet Now
              </Link>
            </div>
          </div>
        </motion.div>
      )}

      {/* Payment Failed Banner */}
      {isPaymentFailed && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-6"
        >
          <div className="flex items-start gap-4">
            <div className="p-2 bg-red-100 dark:bg-red-800 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="font-semibold text-red-800 dark:text-red-300">
                Payment Failed
              </h3>
              <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                {order.payuee_error || 'There was an issue processing your payment through Payuee.'}
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Order Status Progress */}
      {!isOnHold && !isPaymentFailed && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-100 dark:border-gray-700"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-8">
            Order Status
          </h2>

          <div className="relative">
            {/* Progress Line */}
            <div className="absolute top-5 left-0 right-0 h-1 bg-gray-200 dark:bg-gray-700 -translate-y-1/2">
              <div
                className="h-full bg-purple-600 transition-all duration-500"
                style={{ width: `${(currentStep / (statusSteps.length - 1)) * 100}%` }}
              />
            </div>

            {/* Steps */}
            <div className="relative flex justify-between">
              {statusSteps.map((step, index) => {
                const isCompleted = index <= currentStep;
                const isCurrent = index === currentStep;

                return (
                  <div key={step.key} className="flex flex-col items-center">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                        isCompleted
                          ? 'bg-purple-600 border-purple-600 text-white'
                          : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-400'
                      } ${isCurrent ? 'ring-4 ring-purple-600/20' : ''}`}
                    >
                      <step.icon className="w-5 h-5" />
                    </div>
                    <span
                      className={`mt-2 text-sm font-medium ${
                        isCompleted
                          ? 'text-purple-600 dark:text-purple-400'
                          : 'text-gray-400'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </motion.div>
      )}

      {/* Payuee Escrow Status */}
      {order.payuee_escrow_status && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Shield className="w-5 h-5 text-blue-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Escrow Status
            </h2>
          </div>

          <div className="relative">
            <div className="absolute top-4 left-0 right-0 h-0.5 bg-gray-200 dark:bg-gray-700">
              <div
                className="h-full bg-blue-600 transition-all duration-500"
                style={{ width: `${(escrowStep / (escrowStates.length - 1)) * 100}%` }}
              />
            </div>

            <div className="relative flex justify-between">
              {escrowStates.map((state, index) => {
                const isCompleted = index <= escrowStep;
                const isCurrent = index === escrowStep;

                return (
                  <div key={state.key} className="flex flex-col items-center max-w-[80px]">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all ${
                        isCompleted
                          ? 'bg-blue-600 border-blue-600 text-white'
                          : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-400'
                      } ${isCurrent ? 'ring-4 ring-blue-600/20' : ''}`}
                    >
                      <div className="w-2 h-2 rounded-full bg-current" />
                    </div>
                    <span className={`mt-2 text-xs font-medium text-center ${
                      isCompleted ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'
                    }`}>
                      {state.label}
                    </span>
                    <span className="text-[10px] text-gray-400 text-center mt-0.5 hidden sm:block">
                      {state.desc}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Payuee Order IDs */}
          {order.payuee_order_ids && order.payuee_order_ids.length > 0 && (
            <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                Payuee Order {order.payuee_order_ids.length > 1 ? 'IDs' : 'ID'}
              </p>
              <div className="flex flex-wrap gap-2">
                {order.payuee_order_ids.map((id: string | number) => (
                  <span 
                    key={id} 
                    className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm font-mono text-gray-700 dark:text-gray-300"
                  >
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* QR Verification Info (for delivered orders) */}
      {order.status === 'delivered' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-2xl p-6"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-800 rounded-lg">
              <QrCode className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h3 className="font-semibold text-green-800 dark:text-green-300">
                Delivery Verified
              </h3>
              <p className="text-sm text-green-700 dark:text-green-400">
                This order was verified via QR code scan and transaction PIN. Escrow funds have been released.
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Order Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Items */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Order Items
          </h2>
          <div className="space-y-4">
            {order.items.map((item: any) => (
              <div key={item.id} className="flex gap-4">
                <img
                  src={item.product_image || '/placeholder.png'}
                  alt={item.product_name}
                  className="w-20 h-20 object-cover rounded-lg bg-gray-100 dark:bg-gray-700"
                />
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white">
                    {item.product_name}
                  </p>
                  {item.selected_size && (
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Size: {item.selected_size}
                    </p>
                  )}
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Qty: {item.quantity}
                  </p>
                  <p className="text-purple-600 font-semibold">
                    {formatPrice(item.total_price)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Shipping & Payment */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-6"
        >
          {/* Shipping Info */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Shipping Information
            </h2>
            <div className="space-y-2 text-gray-600 dark:text-gray-400">
              <p className="font-medium text-gray-900 dark:text-white">
                {order.shipping_name}
              </p>
              <p>{order.shipping_address}</p>
              <p>
                {order.shipping_city}, {order.shipping_state}{' '}
                {order.shipping_postal_code}
              </p>
              <p>{order.shipping_country}</p>
              <p className="pt-2">{order.shipping_phone}</p>
            </div>

            {order.tracking_number && (
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Tracking Number
                </p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {order.tracking_number}
                </p>
                {order.carrier && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Carrier: {order.carrier}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Order Summary */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Order Summary
            </h2>
            <div className="space-y-2">
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Subtotal</span>
                <span>{formatPrice(order.subtotal)}</span>
              </div>
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Shipping</span>
                <span>{formatPrice(order.shipping_cost)}</span>
              </div>
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Tax</span>
                <span>{formatPrice(order.tax)}</span>
              </div>
              {order.discount > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>Discount</span>
                  <span>-{formatPrice(order.discount)}</span>
                </div>
              )}
              <div className="pt-2 border-t border-gray-200 dark:border-gray-700 flex justify-between">
                <span className="font-semibold text-gray-900 dark:text-white">
                  Total
                </span>
                <span className="text-xl font-bold text-purple-600">
                  {formatPrice(order.total)}
                </span>
              </div>
            </div>

            {/* Payment Status */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Payment Status</span>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  order.payment_status === 'escrow_locked' ? 'bg-emerald-100 text-emerald-700' :
                  order.payment_status === 'on_hold' ? 'bg-orange-100 text-orange-700' :
                  order.payment_status === 'failed' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {order.payment_status?.replace('_', ' ') || 'Pending'}
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Cancel Order Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setShowCancelModal(false)}>
          <motion.form
            onClick={(e) => e.stopPropagation()}
            onSubmit={handleCancelOrder}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-6 w-full max-w-sm space-y-4"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Cancel this order?</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">Enter your Payuee PIN to confirm cancellation.</p>
            <input
              type="password"
              inputMode="numeric"
              maxLength={6}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
              placeholder="6-digit PIN"
              className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-red-500"
            />
            <textarea
              value={reportNote}
              onChange={(e) => setReportNote(e.target.value)}
              placeholder="Reason (optional)"
              rows={2}
              className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-red-500"
            />
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={isSubmittingAction}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white font-semibold rounded-xl hover:bg-red-700 disabled:opacity-50"
              >
                {isSubmittingAction ? 'Cancelling...' : 'Confirm Cancellation'}
              </button>
              <button
                type="button"
                onClick={() => setShowCancelModal(false)}
                className="px-4 py-2.5 text-gray-600 dark:text-gray-300 font-medium"
              >
                Keep Order
              </button>
            </div>
          </motion.form>
        </div>
      )}

      {/* Report Issue Modal */}
      {showReportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setShowReportModal(false)}>
          <motion.form
            onClick={(e) => e.stopPropagation()}
            onSubmit={handleReportOrder}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-6 w-full max-w-sm space-y-4"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Report an issue</h3>
            <textarea
              value={reportNote}
              onChange={(e) => setReportNote(e.target.value)}
              placeholder="Describe the issue with this order..."
              rows={4}
              required
              className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={isSubmittingAction}
                className="flex-1 px-4 py-2.5 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 disabled:opacity-50"
              >
                {isSubmittingAction ? 'Submitting...' : 'Submit Report'}
              </button>
              <button
                type="button"
                onClick={() => setShowReportModal(false)}
                className="px-4 py-2.5 text-gray-600 dark:text-gray-300 font-medium"
              >
                Cancel
              </button>
            </div>
          </motion.form>
        </div>
      )}
    </div>
  );
}