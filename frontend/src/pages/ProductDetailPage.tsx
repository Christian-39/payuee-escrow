/**
 * Product Detail Page
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Heart,
  ShoppingCart,
  Star,
  Truck,
  Shield,
  RotateCcw,
  ChevronRight,
  Minus,
  Plus,
  Check,
  AlertCircle,
  MessageSquare,
  User,
  Share2,
  Info
} from 'lucide-react';
import api from '../lib/api';
import type { Product } from '../types';
import { useCart } from '../contexts/CartContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import ProductCard from '../components/ProductCard';

export default function ProductDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [product, setProduct] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [selectedImage, setSelectedImage] = useState(0);
  const [isWishlisted, setIsWishlisted] = useState(false);
  const [isAddingToCart, setIsAddingToCart] = useState(false);
  const [activeTab, setActiveTab] = useState<'description' | 'specifications' | 'reviews'>('description');
  
  const { addToCart } = useCart();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (slug) {
      fetchProduct();
    }
  }, [slug]);

  const fetchProduct = async () => {
    try {
      setIsLoading(true);
      const response = await api.get(`/products/${slug}/`);
      setProduct(response.data);
      setIsWishlisted(response.data.is_wishlisted);
    } catch (error) {
      toast.error('Failed to load product');
    } finally {
      setIsLoading(false);
    }
  };

  const getImageUrl = (url?: string, source?: string) => {
  if (!url) return '/placeholder.png';

  // If it's already a full URL (Payuee or external), return as-is
  if (url.startsWith('http')) return url;

  // If it's a local relative path, prepend the backend URL
  return `http://localhost:8000${url}`;
  };
  /**
   * Safe Number Formatter
   * Prevents "toFixed is not a function" by forcing conversion to Number
   */
  const formatCurrency = (value: any) => {
    const num = Number(value) || 0;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(num);
  };

  const getRating = (val: any) => {
    return Number(val) || 0;
  };

  const handleAddToCart = async () => {
    if (!product) return;
    
    if (!isAuthenticated) {
      toast.error('Please login to add items to cart');
      return;
    }

    setIsAddingToCart(true);
    try {
      await addToCart(product.id, quantity);
      toast.success(`${product.name} added to cart`);
      setQuantity(1);
    } catch (error) {
      toast.error('Failed to add to cart');
    } finally {
      setIsAddingToCart(false);
    }
  };

  const handleToggleWishlist = async () => {
    if (!product) return;
    
    if (!isAuthenticated) {
      toast.error('Please login to add items to wishlist');
      return;
    }

    try {
      const response = await api.post(`/products/wishlist/toggle/${product.id}/`);
      setIsWishlisted(response.data.in_wishlist);
      toast.success(response.data.message);
    } catch (error) {
      toast.error('Failed to update wishlist');
    }
  };

  const increaseQuantity = () => {
    if (product && quantity < product.quantity) {
      setQuantity((q) => q + 1);
    }
  };

  const decreaseQuantity = () => {
    if (quantity > 1) {
      setQuantity((q) => q - 1);
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success('Link copied to clipboard');
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-8">
        <div className="flex items-center gap-2 h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
          <div className="space-y-4">
            <div className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-2xl" />
            <div className="flex gap-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="w-20 h-20 bg-gray-200 dark:bg-gray-700 rounded-xl" />
              ))}
            </div>
          </div>
          <div className="space-y-6">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
            <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
            </div>
            <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded w-full" />
            <div className="grid grid-cols-3 gap-4">
              <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded-xl" />
              <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded-xl" />
              <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="text-center py-20">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-full mb-6">
          <AlertCircle className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Product Not Found
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-8 max-w-md mx-auto">
          The product you're looking for doesn't exist or has been removed from our catalog.
        </p>
        <Link
          to="/products"
          className="inline-flex items-center gap-2 px-8 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-all shadow-lg shadow-purple-200 dark:shadow-none"
        >
          Browse All Products
        </Link>
      </div>
    );
  }

  const normalizeImages = (images: any) => {
  if (!images) return [];
  if (Array.isArray(images)) return images;
  if (typeof images === 'string') return [images];
  if (typeof images === 'object') return Object.values(images);
  return [];
};

// Build image array based on product source
const allImages = [
  product.featured_image, // This is URLField for both Payuee and local
  ...normalizeImages(product.images) // This is for additional images
].filter(Boolean);

// Debug log
console.log('Product source:', product.source);
console.log('Featured image:', product.featured_image);
console.log('All images:', allImages);

  return (
    <div className="space-y-12 pb-20">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 overflow-x-auto whitespace-nowrap pb-2 lg:pb-0">
        <Link to="/" className="hover:text-purple-600 transition-colors">Home</Link>
        <ChevronRight className="w-4 h-4 flex-shrink-0" />
        <Link to="/products" className="hover:text-purple-600 transition-colors">Products</Link>
        {product.category && (
          <>
            <ChevronRight className="w-4 h-4 flex-shrink-0" />
            <Link
              to={`/products?category=${product.category.slug}`}
              className="hover:text-purple-600 transition-colors"
            >
              {product.category.name}
            </Link>
          </>
        )}
        <ChevronRight className="w-4 h-4 flex-shrink-0" />
        <span className="text-gray-900 dark:text-white font-medium truncate max-w-[200px]">
          {product.name}
        </span>
      </nav>

      {/* Main Product Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16">
        
        {/* Left Column: Media Gallery */}
        <div className="space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="group relative aspect-square bg-gray-100 dark:bg-gray-800 rounded-3xl overflow-hidden border border-gray-200 dark:border-gray-700"
          >
            <img
              src={getImageUrl(allImages[selectedImage])}
              alt={product.name}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            />
            <button 
              onClick={handleShare}
              className="absolute top-4 right-4 p-3 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm rounded-full text-gray-700 dark:text-gray-200 hover:bg-white transition-colors shadow-sm"
            >
              <Share2 className="w-5 h-5" />
            </button>
          </motion.div>

          {allImages.length > 1 && (
            <div className="flex gap-3 overflow-x-auto pb-2 no-scrollbar">
              {allImages.map((image, index) => (
                <button
                  key={index}
                  onClick={() => setSelectedImage(index)}
                  className={cn(
                    'flex-shrink-0 w-24 h-24 rounded-2xl overflow-hidden border-2 transition-all duration-200',
                    selectedImage === index
                      ? 'border-purple-600 ring-2 ring-purple-600/20'
                      : 'border-transparent hover:border-gray-300 dark:hover:border-gray-600'
                  )}
                >
                  <img
                    src={getImageUrl(image)}
                    alt={`${product.name} gallery ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Product Information */}
        <div className="flex flex-col">
          <div className="flex-1 space-y-8">
            <div className="space-y-4">
              {product.category && (
                <Link
                  to={`/products?category=${product.category.slug}`}
                  className="inline-block px-3 py-1 bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 text-xs font-bold uppercase tracking-widest rounded-full hover:bg-purple-100 transition-colors"
                >
                  {product.category.name}
                </Link>
              )}
              <h1 className="text-3xl lg:text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight">
                {product.name}
              </h1>
              
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-1.5">
                  <div className="flex text-yellow-400">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={cn(
                          'w-5 h-5',
                          i < Math.round(getRating(product.average_rating)) ? 'fill-current' : 'text-gray-300 dark:text-gray-600'
                        )}
                      />
                    ))}
                  </div>
                  <span className="text-sm font-bold text-gray-900 dark:text-white ml-1">
                    {getRating(product.average_rating).toFixed(1)}
                  </span>
                </div>
                <div className="h-4 w-px bg-gray-300 dark:bg-gray-700" />
                <span className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                  {product.review_count} Verified Reviews
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-4">
                <span className="text-4xl font-black text-gray-900 dark:text-white tracking-tighter">
                  {formatCurrency(product.price)}
                </span>
                {product.compare_at_price && (
                  <span className="text-2xl text-gray-400 line-through font-medium">
                    {formatCurrency(product.compare_at_price)}
                  </span>
                )}
              </div>
              {product.discount_percentage > 0 && (
                <div className="inline-flex items-center gap-1.5 text-red-600 dark:text-red-400 font-bold text-sm bg-red-50 dark:bg-red-900/20 px-3 py-1 rounded-lg">
                  <Check className="w-4 h-4" />
                  Special Offer: Save {product.discount_percentage}% today
                </div>
              )}
            </div>

            <p className="text-lg text-gray-600 dark:text-gray-400 leading-relaxed max-w-xl">
              {product.short_description || (product.description && product.description.substring(0, 180) + '...')}
            </p>

            <div className="space-y-6">
              <div className="flex items-center gap-3">
                {product.is_in_stock ? (
                  <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold bg-emerald-50 dark:bg-emerald-900/20 px-4 py-2 rounded-xl border border-emerald-100 dark:border-emerald-800/50">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    Available in Stock
                    {product.is_low_stock && (
                      <span className="ml-2 px-2 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 text-xs rounded-md">
                        Only {product.quantity} left!
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-bold bg-red-50 dark:bg-red-900/20 px-4 py-2 rounded-xl border border-red-100 dark:border-red-800/50">
                    <AlertCircle className="w-5 h-5" />
                    Currently Out of Stock
                  </div>
                )}
              </div>

              {product.is_in_stock && (
                <div className="flex flex-col sm:flex-row gap-4">
                  <div className="flex items-center bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-2xl p-1">
                    <button
                      onClick={decreaseQuantity}
                      disabled={quantity <= 1}
                      className="p-3 text-gray-600 dark:text-gray-400 hover:bg-white dark:hover:bg-gray-700 rounded-xl disabled:opacity-30 transition-all"
                    >
                      <Minus className="w-5 h-5" />
                    </button>
                    <span className="w-14 text-center text-lg font-bold text-gray-900 dark:text-white">
                      {quantity}
                    </span>
                    <button
                      onClick={increaseQuantity}
                      disabled={quantity >= product.quantity}
                      className="p-3 text-gray-600 dark:text-gray-400 hover:bg-white dark:hover:bg-gray-700 rounded-xl disabled:opacity-30 transition-all"
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                  </div>

                  <button
                    onClick={handleAddToCart}
                    disabled={isAddingToCart}
                    className="flex-1 flex items-center justify-center gap-3 px-8 py-4 bg-purple-600 text-white font-bold rounded-2xl hover:bg-purple-700 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-xl shadow-purple-600/20 dark:shadow-none"
                  >
                    {isAddingToCart ? (
                      <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <>
                        <ShoppingCart className="w-6 h-6" />
                        Add to Cart — {formatCurrency(Number(product.price) * quantity)}
                      </>
                    )}
                  </button>

                  <button
                    onClick={handleToggleWishlist}
                    className={cn(
                      'p-4 rounded-2xl border-2 transition-all duration-300 active:scale-90',
                      isWishlisted
                        ? 'border-red-500 bg-red-50 dark:bg-red-900/20 text-red-500 shadow-lg shadow-red-500/10'
                        : 'border-gray-200 dark:border-gray-700 text-gray-400 hover:border-purple-600 hover:text-purple-600'
                    )}
                  >
                    <Heart className={cn('w-7 h-7', isWishlisted && 'fill-current')} />
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-10 pt-8 border-t border-gray-100 dark:border-gray-800">
            <div className="flex flex-col items-center text-center gap-2">
              <div className="w-12 h-12 bg-purple-50 dark:bg-purple-900/20 rounded-full flex items-center justify-center text-purple-600">
                <Truck className="w-6 h-6" />
              </div>
              <span className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-tighter">Fast Delivery</span>
            </div>
            <div className="flex flex-col items-center text-center gap-2">
              <div className="w-12 h-12 bg-purple-50 dark:bg-purple-900/20 rounded-full flex items-center justify-center text-purple-600">
                <Shield className="w-6 h-6" />
              </div>
              <span className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-tighter">Official Warranty</span>
            </div>
            <div className="flex flex-col items-center text-center gap-2">
              <div className="w-12 h-12 bg-purple-50 dark:bg-purple-900/20 rounded-full flex items-center justify-center text-purple-600">
                <RotateCcw className="w-6 h-6" />
              </div>
              <span className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-tighter">Easy Returns</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Section */}
      <div className="pt-10">
        <div className="flex items-center gap-8 border-b border-gray-200 dark:border-gray-800 mb-8 overflow-x-auto no-scrollbar">
          {(['description', 'specifications', 'reviews'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'pb-4 text-sm font-bold uppercase tracking-widest transition-all relative whitespace-nowrap',
                activeTab === tab 
                  ? 'text-purple-600' 
                  : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-200'
              )}
            >
              {tab}
              {activeTab === tab && (
                <motion.div layoutId="tab-indicator" className="absolute bottom-0 left-0 right-0 h-1 bg-purple-600 rounded-full" />
              )}
            </button>
          ))}
        </div>

        <div className="min-h-[300px]">
          <AnimatePresence mode="wait">
            {activeTab === 'description' && (
              <motion.div
                key="description"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="prose prose-purple dark:prose-invert max-w-none"
              >
                <div className="bg-white dark:bg-gray-900 p-8 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm">
                  <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <Info className="w-5 h-5 text-purple-600" />
                    Product Overview
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 whitespace-pre-line leading-relaxed text-lg">
                    {product.description}
                  </p>
                </div>
              </motion.div>
            )}

            {activeTab === 'specifications' && (
              <motion.div
                key="specs"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-4"
              >
                {product.specifications && Object.entries(product.specifications).length > 0 ? (
                  Object.entries(product.specifications).map(([key, value]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between p-5 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-gray-100 dark:border-gray-700/50"
                    >
                      <span className="text-gray-500 dark:text-gray-400 font-medium capitalize">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span className="font-bold text-gray-900 dark:text-white">
                        {value as string}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="col-span-2 text-center py-10 text-gray-500">
                    No technical specifications provided for this item.
                  </div>
                )}
              </motion.div>
            )}

            {activeTab === 'reviews' && (
              <motion.div
                key="reviews"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-purple-50 dark:bg-purple-900/10 p-6 rounded-3xl">
                  <div>
                    <h3 className="text-2xl font-black text-gray-900 dark:text-white">Customer Feedback</h3>
                    <p className="text-gray-500 dark:text-gray-400">Based on {product.review_count} recent purchases</p>
                  </div>
                  <button className="px-6 py-3 bg-white dark:bg-gray-800 text-purple-600 dark:text-purple-400 font-bold rounded-xl shadow-sm hover:shadow-md transition-all">
                    Write a Review
                  </button>
                </div>

                {product.reviews && product.reviews.length > 0 ? (
                  <div className="grid grid-cols-1 gap-6">
                    {product.reviews.map((review: any) => (
                      <div key={review.id} className="bg-white dark:bg-gray-900 p-6 rounded-3xl border border-gray-100 dark:border-gray-800">
                        <div className="flex flex-wrap justify-between items-start gap-4 mb-4">
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center">
                              <User className="w-6 h-6 text-gray-400" />
                            </div>
                            <div>
                              <p className="font-bold text-gray-900 dark:text-white">{review.user_name}</p>
                              <div className="flex text-yellow-400 mt-0.5">
                                {[...Array(5)].map((_, i) => (
                                  <Star key={i} className={cn('w-3.5 h-3.5', i < getRating(review.rating) ? 'fill-current' : 'text-gray-200 dark:text-gray-700')} />
                                ))}
                              </div>
                            </div>
                          </div>
                          <span className="text-xs font-medium text-gray-400 bg-gray-50 dark:bg-gray-800 px-3 py-1 rounded-full">
                            {new Date(review.created_at).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}
                          </span>
                        </div>
                        <p className="text-gray-600 dark:text-gray-400 leading-relaxed italic">
                          "{review.comment}"
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-20 bg-gray-50 dark:bg-gray-800/30 rounded-3xl border-2 border-dashed border-gray-200 dark:border-gray-700">
                    <MessageSquare className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-500 dark:text-gray-400 font-medium text-lg">No reviews yet. Be the first to rate this product!</p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Related Products */}
      {product.related_products && product.related_products.length > 0 && (
        <div className="pt-12 border-t border-gray-100 dark:border-gray-800">
          <h2 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight mb-8">
            You May Also Like
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {product.related_products.map((relatedProduct: any) => (
              <ProductCard key={relatedProduct.id} product={relatedProduct} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}