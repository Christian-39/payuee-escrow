// src/components/PayueePinModal.tsx

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Lock, Eye, EyeOff, Shield, Loader2 } from 'lucide-react';
import api from '../lib/api';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

interface PayueePinModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPinSet: (pin: string) => void;
}

const weakPins = [
  '000000', '111111', '222222', '333333', '444444',
  '555555', '666666', '777777', '888888', '999999', '123456',
  '654321', '121212', '112233', '123123'
];

export default function PayueePinModal({ isOpen, onClose, onPinSet }: PayueePinModalProps) {
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [showPin, setShowPin] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!pin || pin.length !== 6) {
      newErrors.pin = 'PIN must be exactly 6 digits';
    } else if (!/^\d{6}$/.test(pin)) {
      newErrors.pin = 'PIN must contain only numbers';
    } else if (weakPins.includes(pin)) {
      newErrors.pin = 'Please choose a more secure PIN (avoid simple patterns)';
    }

    if (pin !== confirmPin) {
      newErrors.confirmPin = 'PINs do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const response = await api.post('/auth/set-payuee-pin/', {
        payuee_transaction_pin: pin
      });

      toast.success('Payuee PIN set successfully!');
      onPinSet(pin);
      onClose();
      
      // Reset form
      setPin('');
      setConfirmPin('');
      setErrors({});
    } catch (error: any) {
      const msg = error.response?.data?.payuee_transaction_pin?.[0] 
        || error.response?.data?.error 
        || 'Failed to set PIN';
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePinChange = (setter: (val: string) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const digitsOnly = e.target.value.replace(/\D/g, '').slice(0, 6);
    setter(digitsOnly);
    if (errors.pin || errors.confirmPin) setErrors({});
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
          >
            <div className="w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 pointer-events-auto overflow-hidden">
              
              {/* Header */}
              <div className="p-6 pb-4 border-b border-gray-100 dark:border-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-xl">
                      <Lock className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        Set Payuee PIN
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Secure your escrow transactions
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
              </div>

              {/* Info Banner */}
              <div className="px-6 py-3 bg-amber-50 dark:bg-amber-900/20 border-y border-amber-100 dark:border-amber-800">
                <div className="flex items-start gap-2">
                  <Shield className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-amber-700 dark:text-amber-300 leading-relaxed">
                    This 6-digit PIN will be required to confirm delivery and release escrow funds. 
                    Choose a secure PIN and keep it safe.
                  </p>
                </div>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 space-y-5">
                
                {/* PIN Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Enter 6-digit PIN
                  </label>
                  <div className="relative">
                    <input
                      type={showPin ? 'text' : 'password'}
                      value={pin}
                      onChange={handlePinChange(setPin)}
                      maxLength={6}
                      inputMode="numeric"
                      autoComplete="off"
                      placeholder="••••••"
                      className={cn(
                        "w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl text-center text-2xl font-mono tracking-[0.5em] focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all",
                        errors.pin 
                          ? "border-red-300 dark:border-red-700 focus:ring-red-500" 
                          : "border-gray-200 dark:border-gray-700"
                      )}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPin(!showPin)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    >
                      {showPin ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {errors.pin && (
                    <p className="mt-1.5 text-sm text-red-600 dark:text-red-400">{errors.pin}</p>
                  )}
                </div>

                {/* Confirm PIN Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Confirm PIN
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirm ? 'text' : 'password'}
                      value={confirmPin}
                      onChange={handlePinChange(setConfirmPin)}
                      maxLength={6}
                      inputMode="numeric"
                      autoComplete="off"
                      placeholder="••••••"
                      className={cn(
                        "w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl text-center text-2xl font-mono tracking-[0.5em] focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all",
                        errors.confirmPin 
                          ? "border-red-300 dark:border-red-700 focus:ring-red-500" 
                          : "border-gray-200 dark:border-gray-700"
                      )}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(!showConfirm)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    >
                      {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {errors.confirmPin && (
                    <p className="mt-1.5 text-sm text-red-600 dark:text-red-400">{errors.confirmPin}</p>
                  )}
                </div>

                {/* Security Requirements */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      pin.length === 6 ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
                    )} />
                    <span className={cn(
                      pin.length === 6 ? "text-green-600 dark:text-green-400" : "text-gray-500 dark:text-gray-400"
                    )}>
                      Exactly 6 digits
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      /^\d{6}$/.test(pin) ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
                    )} />
                    <span className={cn(
                      /^\d{6}$/.test(pin) ? "text-green-600 dark:text-green-400" : "text-gray-500 dark:text-gray-400"
                    )}>
                      Numbers only
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      !weakPins.includes(pin) && pin.length === 6 ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
                    )} />
                    <span className={cn(
                      !weakPins.includes(pin) && pin.length === 6 ? "text-green-600 dark:text-green-400" : "text-gray-500 dark:text-gray-400"
                    )}>
                      Not a common/weak PIN
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      pin === confirmPin && pin.length === 6 ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
                    )} />
                    <span className={cn(
                      pin === confirmPin && pin.length === 6 ? "text-green-600 dark:text-green-400" : "text-gray-500 dark:text-gray-400"
                    )}>
                      PINs match
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="flex-1 px-4 py-3 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting || pin.length !== 6 || confirmPin.length !== 6}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white font-medium rounded-xl hover:bg-purple-700 disabled:opacity-50 transition-colors"
                  >
                    {isSubmitting ? (
                      <><Loader2 className="w-4 h-4 animate-spin" />Setting...</>
                    ) : (
                      <><Lock className="w-4 h-4" />Set PIN</>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}