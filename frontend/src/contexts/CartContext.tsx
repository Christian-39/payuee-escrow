/**
 * Cart Context - Shopping Cart Management
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'; // ← Add useCallback
import { toast } from 'sonner';
import api from '../lib/api';
import type { Cart, CartItem } from '../types';

interface CartContextType {
  cart: Cart | null;
  isLoading: boolean;
  addToCart: (productId: string, quantity?: number) => Promise<void>;
  updateQuantity: (itemId: string, quantity: number) => Promise<void>;
  removeFromCart: (itemId: string) => Promise<void>;
  clearCart: () => Promise<void>;
  refreshCart: () => Promise<void>;
  cartCount: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // ✅ WRAPPED IN useCallback - stable reference
  const refreshCart = useCallback(async () => {
    try {
      const response = await api.get('/orders/cart/');
      setCart(response.data);
    } catch (error) {
      setCart(null);
    }
  }, []); // ← Empty deps = never recreates

  // Fetch cart on mount if user is authenticated
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      refreshCart();
    }
  }, [refreshCart]); // ← Now safe to include

  // ✅ WRAPPED IN useCallback
  const addToCart = useCallback(async (productId: string, quantity: number = 1) => {
    setIsLoading(true);
    try {
      const response = await api.post('/orders/cart/add/', {
        product_id: productId,
        quantity,
      });
      setCart(response.data.cart);
      toast.success('Added to cart!');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to add to cart';
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []); // ← No external dependencies

  // ✅ WRAPPED IN useCallback
  const updateQuantity = useCallback(async (itemId: string, quantity: number) => {
    setIsLoading(true);
    try {
      const response = await api.patch(`/orders/cart/update/${itemId}/`, {
        quantity,
      });
      setCart(response.data.cart);
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to update cart';
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ✅ WRAPPED IN useCallback
  const removeFromCart = useCallback(async (itemId: string) => {
    setIsLoading(true);
    try {
      const response = await api.delete(`/orders/cart/remove/${itemId}/`);
      setCart(response.data.cart);
      toast.success('Item removed from cart');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to remove item';
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ✅ WRAPPED IN useCallback
  const clearCart = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.delete('/orders/cart/clear/');
      setCart(response.data.cart);
      toast.success('Cart cleared');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to clear cart';
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ✅ useMemo for computed value (optional but good practice)
  const cartCount = cart?.total_items || 0;

  return (
    <CartContext.Provider
      value={{
        cart,
        isLoading,
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        refreshCart,
        cartCount,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}