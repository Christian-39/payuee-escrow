/**
 * Product Card Component
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Heart, ShoppingCart, Star } from 'lucide-react';
import type { ProductListItem } from '../types/index';
import { useCart } from '../contexts/CartContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import api from '../lib/api';
import { cn } from '../lib/utils';

interface ProductCardProps {
  product: ProductListItem;
}

// 💰 Helper for price formatting (comma + 2 decimals)
const formatPrice = (price: any) => {
  return Number(price || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

export default function ProductCard({ product }: ProductCardProps) {
  const [isWishlisted, setIsWishlisted] = useState(product.is_wishlisted);
  const [isAddingToCart, setIsAddingToCart] = useState(false);
  const { addToCart } = useCart();
  const { isAuthenticated } = useAuth();

  const BASE_URL = "http://127.0.0.1:8000";

  const handleAddToCart = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!isAuthenticated) {
      toast.error('Please login to add items to cart');
      return;
    }

    setIsAddingToCart(true);
    try {
      await addToCart(product.id, 1);
      toast.success('Added to cart');
    } catch {
      toast.error('Failed to add to cart');
    } finally {
      setIsAddingToCart(false);
    }
  };

  const handleToggleWishlist = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!isAuthenticated) {
      toast.error('Please login to add items to wishlist');
      return;
    }

    try {
      const response = await api.post(`/products/wishlist/toggle/${product.id}/`);
      setIsWishlisted(response.data.in_wishlist);
      toast.success(response.data.message);
    } catch {
      toast.error('Failed to update wishlist');
    }
  };

  // Helper to determine image source
  const getProductImage = () => {
    const imgPath = product.featured_image || product.featured_image; // Check both naming possibilities
    if (!imgPath) return '/placeholder-product.png';
    return imgPath.startsWith('http') ? imgPath : `${BASE_URL}${imgPath}`;
  };

  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="group relative bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300"
    >
      {/* Image Container */}
      <Link
        to={`/products/${product.slug}`}
        className="block relative aspect-[4/3] overflow-hidden bg-gray-100 dark:bg-gray-700"
      >
        <img
          src={getProductImage()}
          alt={product.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />

        {/* Badges */}
        <div className="absolute top-3 left-3 flex flex-col gap-2">
          {product.discount_percentage > 0 && (
            <span className="px-3 py-1 bg-red-500 text-white text-xs font-bold rounded-full shadow-sm">
              -{product.discount_percentage}%
            </span>
          )}
          {product.is_featured && (
            <span className="px-3 py-1 bg-purple-600 text-white text-xs font-bold rounded-full shadow-sm">
              Featured
            </span>
          )}
        </div>

        {/* Out of Stock Overlay */}
        {!product.is_in_stock && (
          <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px] flex items-center justify-center">
            <span className="px-4 py-2 bg-gray-900 text-white text-sm font-semibold rounded-lg">
              Out of Stock
            </span>
          </div>
        )}

        {/* Hover Action: Add to Cart */}
        <div className="absolute bottom-3 left-3 right-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-2 group-hover:translate-y-0">
          <button
            onClick={handleAddToCart}
            disabled={!product.is_in_stock || isAddingToCart}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm transition-all',
              product.is_in_stock
                ? 'bg-purple-600 text-white hover:bg-purple-700 shadow-lg shadow-purple-500/30'
                : 'bg-gray-400 text-gray-200 cursor-not-allowed'
            )}
          >
            {isAddingToCart ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <ShoppingCart className="w-4 h-4" />
                Add to Cart
              </>
            )}
          </button>
        </div>
      </Link>

      {/* Content */}
      <div className="p-4">
        {/* Category */}
        <p className="text-xs text-purple-600 dark:text-purple-400 font-medium mb-1 uppercase tracking-wider">
          {product.category?.name || 'Gadgets'}
        </p>

        {/* Name */}
        <Link to={`/products/${product.slug}`}>
          <h3 className="font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors h-12">
            {product.name}
          </h3>
        </Link>

        {/* Rating */}
        <div className="flex items-center gap-1 mb-3">
          <div className="flex items-center">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                className={cn(
                  'w-3.5 h-3.5',
                  i < Math.round(product.average_rating)
                    ? 'text-yellow-400 fill-yellow-400'
                    : 'text-gray-300 dark:text-gray-600'
                )}
              />
            ))}
          </div>
          <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
            ({product.review_count})
          </span>
        </div>

        {/* Price & Wishlist Row */}
        <div className="flex items-center justify-between mt-auto">
          <div className="flex flex-col">
            <span className="text-lg font-bold text-gray-900 dark:text-white">
              ₦{formatPrice(product.price)}
            </span>
            {product.compare_at_price && (
              <span className="text-xs text-gray-400 line-through">
                ₦{formatPrice(product.compare_at_price)}
              </span>
            )}
          </div>

          <button
            onClick={handleToggleWishlist}
            className={cn(
              'p-2.5 rounded-xl transition-all duration-200',
              isWishlisted
                ? 'bg-red-50 dark:bg-red-900/20 text-red-500'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
            )}
          >
            <Heart
              className={cn(
                'w-5 h-5 transition-transform',
                isWishlisted && 'fill-current scale-110'
              )}
            />
          </button>
        </div>
      </div>
    </motion.div>
  );
}