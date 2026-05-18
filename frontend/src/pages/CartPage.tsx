/**
 * Cart Page with Shipping Calculation
 */

import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Trash2, Minus, Plus, ShoppingBag, ArrowRight, Package, Truck, Loader2 } from 'lucide-react';
import { useCart } from '../contexts/CartContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import api from '../lib/api';

interface ShippingOption {
  vendor_id: number;
  fee: number;
  method_id: string;
  config_id: number;
  company_name: string;
}

interface CartProduct {
  id: number | string;
  name: string;
  slug: string;
  price: number;
  featured_image: string;
  eshop_user_id?: number;
  payuee_vendor_id?: number;
  vendor_id?: number;
  // CRITICAL FIX: payuee_product_id must be present for Payuee API calls
  payuee_product_id?: number | null;
  category?: { name: string; slug: string };
}

interface CartItem {
  id: string;
  product: CartProduct;
  quantity: number;
  total_price: number;
  size?: string;
}

export default function CartPage() {
  const { cart, isLoading, updateQuantity, removeFromCart, refreshCart } = useCart();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [shippingOptions, setShippingOptions] = useState<ShippingOption[]>([]);
  const [isCalculatingShipping, setIsCalculatingShipping] = useState(false);
  const [shippingError, setShippingError] = useState('');
  const [selectedLocation, setSelectedLocation] = useState<any>(null);

  useEffect(() => {
    if (isAuthenticated) {
      refreshCart();
    }
  }, [isAuthenticated, refreshCart]);

  const handleQuantityChange = async (itemId: string, newQuantity: number) => {
    if (newQuantity < 1) return;
    try {
      await updateQuantity(itemId, newQuantity);
      // Recalculate shipping if location is selected
      if (selectedLocation) {
        calculateShipping(selectedLocation);
      }
    } catch (error) {
      // Error handled in context
    }
  };

  const handleRemove = async (itemId: string) => {
    try {
      await removeFromCart(itemId);
      // Recalculate shipping if location is selected
      if (selectedLocation && cart?.items.length > 1) {
        calculateShipping(selectedLocation);
      } else {
        setShippingOptions([]);
      }
    } catch (error) {
      // Error handled in context
    }
  };

  const calculateShipping = async (location: any) => {
    if (!cart || cart.items.length === 0) return;

    setIsCalculatingShipping(true);
    setShippingError('');

    try {
      const cartItemsForShipping = [];

      for (const item of cart.items as CartItem[]) {
        // CRITICAL FIX: Use payuee_vendor_id (mapped from payuee_vendor_id on backend)
        const eshopUserId = item.product.eshop_user_id 
          || item.product.payuee_vendor_id 
          || item.product.vendor_id;

        const vendorId = parseInt(String(eshopUserId), 10);

        if (!vendorId || isNaN(vendorId) || vendorId <= 0) {
          setShippingError(`"${item.product.name}" is missing vendor info. Remove and re-add to cart.`);
          setIsCalculatingShipping(false);
          return;
        }

        // CRITICAL FIX: ONLY use payuee_product_id. NEVER fall back to local UUID (item.product.id).
        if (!item.product.payuee_product_id) {
          setShippingError(`"${item.product.name}" is not linked to Payuee. Please remove and re-add to cart.`);
          setIsCalculatingShipping(false);
          return;
        }

        const productId = parseInt(String(item.product.payuee_product_id), 10);
        if (isNaN(productId) || productId <= 0) {
          setShippingError(`"${item.product.name}" has invalid Payuee product ID.`);
          setIsCalculatingShipping(false);
          return;
        }

        cartItemsForShipping.push({
          product_id: productId,
          eshop_user_id: vendorId,
          quantity: item.quantity,
        });
      }

      const vendors = [...new Set(cartItemsForShipping.map((item) => item.eshop_user_id))];

      const response = await api.post('/payments/shipping-fees/', {
        vendors,
        state: location.state,
        city: location.city,
        latitude: location.latitude,
        longitude: location.longitude,
        cart_items: cartItemsForShipping,
      });

      if (response.data.success) {
        setShippingOptions(response.data.shipping || []);
        setShippingError('');
      } else {
        setShippingError(response.data.error || 'Shipping calculation failed');
        setShippingOptions([]);
      }

    } catch (error: any) {
      console.error('Shipping error:', error);
      const msg = error.response?.data?.error || error.message || 'Failed to calculate shipping';
      setShippingError(msg);
      setShippingOptions([]);
    } finally {
      setIsCalculatingShipping(false);
    }
  };

  const handleLocationSelect = () => {
    // Navigate to checkout for location selection, or open a modal
    // For now, navigate to checkout where location is selected
    navigate('/checkout');
  };

  const handleCheckout = () => {
    if (!isAuthenticated) {
      toast.error('Please login to proceed to checkout');
      navigate('/login');
      return;
    }
    navigate('/checkout');
  };

  // Calculate totals with shipping
  const shippingCost = shippingOptions.reduce((a, b) => a + b.fee, 0);
  const subtotal = cart?.subtotal || 0;
  const tax = subtotal * 0.08;
  const total = subtotal + shippingCost + tax;

  if (!isAuthenticated) {
    return (
      <div className="text-center py-16">
        <div className="w-24 h-24 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
          <ShoppingBag className="w-12 h-12 text-purple-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Your Cart is Waiting
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
          Please login to view your cart and continue shopping
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

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
            ))}
          </div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="w-24 h-24 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-6">
          <Package className="w-12 h-12 text-gray-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Your Cart is Empty
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
          Looks like you haven't added anything to your cart yet
        </p>
        <Link
          to="/products"
          className="inline-flex items-center gap-2 px-8 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors"
        >
          <ShoppingBag className="w-5 h-5" />
          Start Shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        Shopping Cart ({cart.total_items} items)
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-2 space-y-4">
          {cart.items.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="flex gap-4 p-4 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700"
            >
              <Link
                to={`/products/${item.product.slug}`}
                className="flex-shrink-0 w-24 h-24 bg-gray-100 dark:bg-gray-700 rounded-xl overflow-hidden"
              >
                <img
                  src={item.product.featured_image}
                  alt={item.product.name}
                  className="w-full h-full object-cover"
                />
              </Link>

              <div className="flex-1 min-w-0">
                <Link
                  to={`/products/${item.product.slug}`}
                  className="font-semibold text-gray-900 dark:text-white hover:text-purple-600 dark:hover:text-purple-400 transition-colors line-clamp-2"
                >
                  {item.product.name}
                </Link>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {item.product.category?.name}
                </p>
                <p className="text-lg font-bold text-purple-600 mt-2">
                  ₦{Number(item.product.price).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </p>
                {item.product.eshop_user_id && (
                  <p className="text-xs text-gray-400 mt-1">
                    Vendor ID: {item.product.eshop_user_id}
                  </p>
                )}
                {/* DEBUG: Show Payuee Product ID */}
                {item.product.payuee_product_id && (
                  <p className="text-xs text-blue-400 mt-1">
                    Payuee PID: {item.product.payuee_product_id}
                  </p>
                )}
              </div>

              <div className="flex flex-col items-end justify-between">
                <button
                  onClick={() => handleRemove(item.id)}
                  className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="w-5 h-5" />
                </button>

                <div className="flex items-center border border-gray-200 dark:border-gray-700 rounded-lg">
                  <button
                    onClick={() => handleQuantityChange(item.id, item.quantity - 1)}
                    disabled={item.quantity <= 1}
                    className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 rounded-l-lg transition-colors"
                  >
                    <Minus className="w-4 h-4" />
                  </button>
                  <span className="w-10 text-center font-medium text-gray-900 dark:text-white text-sm">
                    {item.quantity}
                  </span>
                  <button
                    onClick={() => handleQuantityChange(item.id, item.quantity + 1)}
                    className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-r-lg transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Order Summary */}
        <div className="lg:sticky lg:top-8 h-fit space-y-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              Order Summary
            </h2>

            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Subtotal ({cart.total_items} items)</span>
                <span>
                  ₦{Number(cart.subtotal).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </span>
              </div>

              {/* Shipping Display */}
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span className="flex items-center gap-2">
                  <Truck className="w-4 h-4" />
                  Shipping
                </span>
                {isCalculatingShipping ? (
                  <span className="flex items-center gap-1 text-blue-600">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Calculating...
                  </span>
                ) : shippingCost > 0 ? (
                  <span>₦{Number(shippingCost).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}</span>
                ) : (
                  <span className="text-green-600">Calculated at checkout</span>
                )}
              </div>

              {/* Tax Display */}
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Tax (8%)</span>
                <span>₦{Number(tax).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}</span>
              </div>

              {/* Shipping Options Detail */}
              {shippingOptions.length > 0 && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-100 dark:border-green-800">
                  <h4 className="text-xs font-semibold text-green-800 dark:text-green-300 mb-2 uppercase tracking-wider">
                    Shipping Options
                  </h4>
                  {shippingOptions.map((opt, i) => (
                    <div key={i} className="flex justify-between items-center text-sm text-green-700 dark:text-green-400">
                      <span>{opt.company_name}</span>
                      <span className="font-semibold">₦{Number(opt.fee).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}</span>
                    </div>
                  ))}
                </div>
              )}

              {shippingError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-xl">
                  {shippingError}
                </div>
              )}
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-6">
              <div className="flex justify-between">
                <span className="font-semibold text-gray-900 dark:text-white">
                  Total
                </span>
                <span className="text-xl font-bold text-purple-600">
                  ₦{Number(total).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </span>
              </div>
            </div>

            <button
              onClick={handleCheckout}
              className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors"
            >
              Proceed to Checkout
              <ArrowRight className="w-5 h-5" />
            </button>

            <Link
              to="/products"
              className="block text-center mt-4 text-purple-600 hover:text-purple-700 font-medium"
            >
              Continue Shopping
            </Link>
          </div>

          {/* Location Selector Hint */}
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-2xl p-4 border border-blue-100 dark:border-blue-800">
            <div className="flex items-start gap-3">
              <Truck className="w-5 h-5 text-blue-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
                  Shipping calculated at checkout
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                  Enter your delivery location during checkout to see exact shipping fees from vendors.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
