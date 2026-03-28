/**
 * Order Tracking Page
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Package, Truck, CheckCircle, Clock, ChevronLeft } from 'lucide-react';
import api from '../lib/api';
import type { Order } from '../types';
import { toast } from 'sonner';
import { formatDate, formatPrice } from '../lib/utils';

const statusSteps = [
  { key: 'pending', label: 'Order Placed', icon: Clock },
  { key: 'confirmed', label: 'Confirmed', icon: CheckCircle },
  { key: 'processing', label: 'Processing', icon: Package },
  { key: 'shipped', label: 'Shipped', icon: Truck },
  { key: 'delivered', label: 'Delivered', icon: CheckCircle },
];

export default function OrderTrackingPage() {
  const { orderNumber } = useParams<{ orderNumber: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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

  const getCurrentStep = () => {
    if (!order) return 0;
    const stepIndex = statusSteps.findIndex((s) => s.key === order.status);
    return stepIndex >= 0 ? stepIndex : 0;
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
      </div>

      {/* Tracking Progress */}
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

      {/* Order Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Items */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Order Items
          </h2>
          <div className="space-y-4">
            {order.items.map((item) => (
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
          transition={{ delay: 0.2 }}
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
          </div>
        </motion.div>
      </div>
    </div>
  );
}
