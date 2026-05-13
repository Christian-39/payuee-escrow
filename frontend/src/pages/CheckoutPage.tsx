/**
 * Checkout Page with Payuee Location Integration
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CreditCard, Truck, Shield, MapPin, Loader2, ChevronDown, Lock } from 'lucide-react';
import api from '../lib/api';
import { useCart } from '../contexts/CartContext';
import { toast } from 'sonner';
import { usePayueeLocation } from '../hooks/usePayueeLocation';
import { cn } from '../lib/utils';

const safeFixed = (value: any, digits = 2) => {
  const num = Number(value);
  return isNaN(num)
    ? (0).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
    : num.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
};

interface CheckoutSummary {
  subtotal: number;
  shipping_cost: number;
  tax: number;
  discount: number;
  total: number;
  item_count: number;
}

interface ShippingOption {
  vendor_id: number;
  fee: number;
  method_id: string;
  config_id: number;
  company_name: string;
}

export default function CheckoutPage() {
  const navigate = useNavigate();
  const { cart, refreshCart } = useCart();
  const [isLoading, setIsLoading] = useState(false);
  const [isCalculatingShipping, setIsCalculatingShipping] = useState(false);
  const [summary, setSummary] = useState<CheckoutSummary | null>(null);
  const [shippingOptions, setShippingOptions] = useState<ShippingOption[]>([]);
  const [shippingError, setShippingError] = useState('');

  const {
    states,
    cities,
    selectedState,
    selectedCity,
    loadingStates,
    loadingCities,
    locationError,
    setSelectedState,
    setSelectedCity,
  } = usePayueeLocation();

  const [stateOpen, setStateOpen] = useState(false);
  const [cityOpen, setCityOpen] = useState(false);

  const [formData, setFormData] = useState({
    shipping_name: '',
    shipping_address: '',
    shipping_city: '',
    shipping_state: '',
    shipping_country: 'Nigeria',
    shipping_postal_code: '',
    shipping_phone: '',
    shipping_latitude: '',
    shipping_longitude: '',
    customer_note: '',
    trans_code: '',
    email: '',
  });

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      const response = await api.get('/orders/checkout/summary/');
      setSummary(response.data);
    } catch (error: any) {
      if (error.response?.status === 400) {
        toast.error('Your cart is empty');
        navigate('/cart');
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleStateSelect = (state: string) => {
    setSelectedState(state);
    setStateOpen(false);
    setCityOpen(false);
    setSelectedCity(null);
    setFormData(prev => ({
      ...prev,
      shipping_state: state,
      shipping_city: '',
      shipping_latitude: '',
      shipping_longitude: '',
    }));
    setShippingOptions([]);
  };

  const handleCitySelect = (city: any) => {
    if (!city) return;
    setSelectedCity(city);
    setCityOpen(false);
    setFormData(prev => ({
      ...prev,
      shipping_city: city.display,
      shipping_latitude: String(city.latitude),
      shipping_longitude: String(city.longitude),
    }));
    // Auto-calculate shipping when city is selected
    calculateShipping(city);
  };

  const calculateShipping = async (city: any) => {
    if (!cart || cart.items.length === 0) return;
    
    setIsCalculatingShipping(true);
    setShippingError('');
    
    try {
      // Build cart items with vendor IDs from product data
      const cartItemsForShipping = cart.items.map((item: any) => ({
        product_id: item.product.id,
        eshop_user_id: item.product.eshop_user_id || item.product.vendor_id,
        quantity: item.quantity,
      }));

      // Get unique vendors
      const vendors = [...new Set(cartItemsForShipping.map((item: any) => item.eshop_user_id))];

      const response = await api.post('/payments/shipping-fees/', {
        vendors,
        state: selectedState,
        city: city.city || city.display.split(' - ')[0],
        latitude: city.latitude,
        longitude: city.longitude,
        cart_items: cartItemsForShipping,
      });

      if (response.data.success) {
        setShippingOptions(response.data.shipping || []);
      } else {
        setShippingError(response.data.error || 'Failed to calculate shipping');
      }
    } catch (error: any) {
      setShippingError(error.response?.data?.error || 'Failed to calculate shipping fees');
    } finally {
      setIsCalculatingShipping(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedCity) {
      toast.error('Please select your delivery location');
      return;
    }
    
    if (shippingOptions.length === 0) {
      toast.error('Please wait for shipping calculation');
      return;
    }
    
    // FIX: Correct PIN validation - 6 digits only, no ₦ symbol
    if (!formData.trans_code || formData.trans_code.length !== 6 || !/^\d{6}$/.test(formData.trans_code)) {
      toast.error('Please enter a valid 6-digit Payuee PIN');
      return;
    }
    
    setIsLoading(true);

    try {
      // Build customer object per Payuee API spec
      const customer = {
        email: formData.email || cart.user_email,
        first_name: formData.shipping_name.split(' ')[0] || formData.shipping_name,
        last_name: formData.shipping_name.split(' ').slice(1).join(' ') || '',
        phone_number: formData.shipping_phone,
        state: formData.shipping_state,
        city: formData.shipping_city,
        address_1: formData.shipping_address,
        address_2: '',
        latitude: parseFloat(formData.shipping_latitude),
        longitude: parseFloat(formData.shipping_longitude),
        order_note: formData.customer_note,
        zip_code: formData.shipping_postal_code,
        province: '',
        save_address: true,
      };

      // Build cart_items per Payuee API spec
      const cartItems = cart.items.map((item: any) => ({
        product_id: item.product.id,
        cart_meta: {
          quantity: item.quantity,
          outfit_size: item.size || '',
        },
      }));

      // Build shipping per Payuee API spec
      const shipping = shippingOptions.map((opt: ShippingOption) => ({
        vendor_id: opt.vendor_id,
        fee: opt.fee,
        method_id: opt.method_id,
        config_id: opt.config_id,
        company_name: opt.company_name,
      }));

      // Call Payuee order creation
      const response = await api.post('/payments/orders/create/', {
        trans_code: formData.trans_code,
        customer,
        cart_items: cartItems,
        shipping,
      });

      if (response.data.success) {
        if (response.data.status === 'ON_HOLD') {
          toast.warning(response.data.message || 'Order on hold - please fund your wallet');
          navigate('/wallet');
        } else {
          toast.success('Order placed successfully!');
          refreshCart();
          navigate(`/orders/${response.data.order_ids?.[0]}/confirmation`);
        }
      } else {
        toast.error(response.data.error || 'Failed to create order');
      }
    } catch (error: any) {
      let message = 'Failed to place order';
      if (error.response?.data?.error) message = error.response.data.error;
      if (error.response?.data?.message) message = error.response.data.message;
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (!cart || cart.items.length === 0) {
    return (
      <div className="text-center py-16">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Your cart is empty</h2>
        <button onClick={() => navigate('/products')} className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700">
          Continue Shopping
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-8">Checkout</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Shipping Information */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                  <MapPin className="w-5 h-5 text-purple-600" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Shipping Information</h2>
              </div>

              {locationError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-xl">{locationError}</div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Email *</label>
                  <input type="email" name="email" value={formData.email} onChange={handleChange} required
                    placeholder="your@email.com"
                    className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Full Name *</label>
                  <input type="text" name="shipping_name" value={formData.shipping_name} onChange={handleChange} required
                    className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Address *</label>
                  <input type="text" name="shipping_address" value={formData.shipping_address} onChange={handleChange} required
                    placeholder="Street address, house number..."
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
                  <input type="text" name="shipping_country" value={formData.shipping_country} readOnly
                    className="w-full px-4 py-3 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-500 rounded-xl cursor-not-allowed" />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Postal Code</label>
                  <input type="text" name="shipping_postal_code" value={formData.shipping_postal_code} onChange={handleChange}
                    className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Phone Number *</label>
                  <input type="tel" name="shipping_phone" value={formData.shipping_phone} onChange={handleChange} required
                    placeholder="+234..."
                    className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500" />
                </div>
              </div>

              {selectedCity && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  className="mt-4 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-100 dark:border-purple-800">
                  <div className="flex items-center gap-2 text-sm text-purple-700 dark:text-purple-300">
                    <MapPin className="w-4 h-4" />
                    <span>Coordinates: {selectedCity.latitude.toFixed(4)}, {selectedCity.longitude.toFixed(4)}</span>
                  </div>
                </motion.div>
              )}

              {/* Shipping Options Display */}
              {isCalculatingShipping && (
                <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
                  <div className="flex items-center gap-2 text-sm text-blue-700 dark:text-blue-300">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Calculating shipping fees...</span>
                  </div>
                </div>
              )}

              {shippingError && (
                <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-xl">
                  {shippingError}
                </div>
              )}

              {shippingOptions.length > 0 && (
                <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-100 dark:border-green-800">
                  <h4 className="text-sm font-semibold text-green-800 dark:text-green-300 mb-2">Shipping Options</h4>
                  {shippingOptions.map((opt, i) => (
                    <div key={i} className="flex justify-between items-center text-sm text-green-700 dark:text-green-400">
                      <span>{opt.company_name} ({opt.method_id})</span>
                      <span className="font-semibold">₦{safeFixed(opt.fee, 2)}</span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Payuee Transaction PIN */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
              className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <Lock className="w-5 h-5 text-green-600" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Payment Authorization</h2>
              </div>
              
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Payuee Transaction PIN (6 digits) *
                </label>
                <input 
                  type="password" 
                  name="trans_code" 
                  value={formData.trans_code} 
                  onChange={handleChange} 
                  required
                  maxLength={6}
                  pattern="\d{6}"
                  inputMode="numeric"
                  autoComplete="off"
                  placeholder="Enter 6-digit PIN"
                  className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 tracking-widest text-center text-lg font-mono"
                />
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Your 6-digit Payuee escrow PIN required to authorize payment.
                </p>
              </div>
            </motion.div>

            {/* Order Note */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Order Note (Optional)</h2>
              <textarea name="customer_note" value={formData.customer_note} onChange={handleChange} rows={3}
                placeholder="Add any special instructions..."
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none" />
            </motion.div>

            <button type="submit" disabled={isLoading || !selectedCity || shippingOptions.length === 0 || formData.trans_code.length !== 6}
              className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 disabled:opacity-50 transition-colors">
              {isLoading ? <><Loader2 className="w-5 h-5 animate-spin" />Processing...</> : <><CreditCard className="w-5 h-5" />Place Order</>}
            </button>
          </form>
        </div>

        {/* Order Summary */}
        <div className="lg:sticky lg:top-8 h-fit">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Order Summary</h2>
            <div className="space-y-3 mb-6 max-h-60 overflow-y-auto">
              {cart.items.map((item: any) => (
                <div key={item.id} className="flex gap-3">
                  <img src={item.product.featured_image} alt={item.product.name} className="w-16 h-16 object-cover rounded-lg" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{item.product.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Qty: {item.quantity}</p>
                    <p className="text-sm font-semibold text-purple-600">₦{safeFixed(item.total_price, 2)}</p>
                  </div>
                </div>
              ))}
            </div>
            {summary && (
              <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex justify-between text-gray-600 dark:text-gray-400">
                  <span>Subtotal ({summary.item_count} items)</span>
                  <span>₦{safeFixed(summary.subtotal, 2)}</span>
                </div>
                <div className="flex justify-between text-gray-600 dark:text-gray-400">
                  <span>Shipping</span>
                  <span className={shippingOptions.reduce((a, b) => a + b.fee, 0) > 0 ? '' : 'text-green-600'}>
                    {shippingOptions.reduce((a, b) => a + b.fee, 0) > 0 
                      ? `₦${safeFixed(shippingOptions.reduce((a, b) => a + b.fee, 0), 2)}`
                      : 'Calculated at checkout'}
                  </span>
                </div>
                <div className="flex justify-between text-gray-600 dark:text-gray-400">
                  <span>Tax</span>
                  <span>₦{safeFixed(summary.tax, 2)}</span>
                </div>
                <div className="flex justify-between pt-3 border-t border-gray-200 dark:border-gray-700">
                  <span className="font-semibold text-gray-900 dark:text-white">Total</span>
                  <span className="text-xl font-bold text-purple-600">
                    ₦{safeFixed(summary.total + shippingOptions.reduce((a, b) => a + b.fee, 0), 2)}
                  </span>
                </div>
              </div>
            )}
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700 space-y-3">
              <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
                <Shield className="w-5 h-5 text-green-500" />
                <span>Secure checkout powered by Payuee</span>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
                <Truck className="w-5 h-5 text-purple-500" />
                <span>Shipping calculated per vendor</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}