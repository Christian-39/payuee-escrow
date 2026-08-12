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
  Minus,
  Plus,
  Check,
  AlertCircle,
  MessageSquare,
  Share2,
  Info
} from 'lucide-react';
import api from '../lib/api';
import { useCart } from '../contexts/CartContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
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
    let isMounted = true;
    async function fetchProductDetails() {
      if (!slug) return;
      setIsLoading(true);
      try {
        const response = await api.get(`/products/${slug}/`);
        if (isMounted) {
          setProduct(response.data);
          setIsWishlisted(response.data.is_wishlisted || false);
        }
      } catch (error) {
        console.error('Error getting product profile detail logs:', error);
        toast.error('Failed to view product specification data.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchProductDetails();
    return () => {
      isMounted = false;
    };
  }, [slug]);

  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewRating, setReviewRating] = useState(0);
  const [reviewHoverRating, setReviewHoverRating] = useState(0);
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewComment, setReviewComment] = useState('');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      toast.error('Please login to write a review');
      return;
    }
    if (reviewRating < 1 || reviewRating > 5) {
      toast.error('Please select a rating');
      return;
    }
    if (!reviewComment.trim()) {
      toast.error('Please write a comment');
      return;
    }

    setIsSubmittingReview(true);
    try {
      const response = await api.post(`/products/${slug}/reviews/create/`, {
        rating: reviewRating,
        title: reviewTitle,
        comment: reviewComment,
      });
      setProduct((prev: any) => ({
        ...prev,
        reviews: [response.data, ...(prev.reviews || [])],
        review_count: (prev.review_count || 0) + 1,
      }));
      toast.success('Review submitted!');
      setShowReviewForm(false);
      setReviewRating(0);
      setReviewTitle('');
      setReviewComment('');
    } catch (error: any) {
      const data = error.response?.data;
      const message = typeof data === 'string' ? data
        : Array.isArray(data?.non_field_errors) ? data.non_field_errors[0]
        : Array.isArray(data?.detail) ? data.detail[0]
        : data?.detail || 'Failed to submit review';
      toast.error(message);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handleToggleWishlist = async () => {
    if (!isAuthenticated) {
      toast.error('Please login to modify your items wishlist');
      return;
    }
    try {
      const response = await api.post(`/products/wishlist/toggle/${product?.id}/`);
      setIsWishlisted(response.data.in_wishlist);
      toast.success(response.data.in_wishlist ? 'Added to wishlist' : 'Removed from wishlist');
    } catch (error) {
      toast.error('Could not modify wishlist configurations.');
    }
  };

  const handleAddToCart = async () => {
    if (!product) return;
    setIsAddingToCart(true);
    try {
      await addToCart(product.id, quantity);
      toast.success(`${product.name} added to cart`);
    } catch (error) {
      toast.error('Failed to add product to basket.');
    } finally {
      setIsAddingToCart(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Product Not Found</h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">The requested product profile doesn't exist or is unavailable.</p>
        <Link to="/products" className="px-6 py-2.5 bg-purple-600 text-white font-medium rounded-xl hover:bg-purple-700 transition-colors">
          Back to Catalog
        </Link>
      </div>
    );
  }

  // Fallback to empty values if fields are missing out
  const images = product.images && product.images.length > 0 ? product.images : [product.featured_image || '/placeholder-product.png'];
  const specifications = typeof product.specifications === 'string' ? JSON.parse(product.specifications || '{}') : (product.specifications || {});
  const reviews = product.reviews || [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mb-16">
        {/* Images Gallery */}
        <div className="flex flex-col gap-4">
          <div className="aspect-square w-full relative overflow-hidden rounded-3xl bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            <img src={images[selectedImage]} alt={product.name} className="w-full h-full object-cover" />
            <button onClick={handleToggleWishlist} className="absolute top-4 right-4 p-3 rounded-2xl bg-white/80 dark:bg-gray-900/80 backdrop-blur-md shadow-sm hover:bg-white dark:hover:bg-gray-900 transition-colors">
              <Heart className={`w-6 h-6 ${isWishlisted ? 'fill-red-500 text-red-500' : 'text-gray-600 dark:text-gray-400'}`} />
            </button>
          </div>
          {images.length > 1 && (
            <div className="flex gap-4 overflow-x-auto pb-2">
              {images.map((img: string, idx: number) => (
                <button key={idx} onClick={() => setSelectedImage(idx)} className={`w-24 h-24 rounded-2xl overflow-hidden border-2 transition-all flex-shrink-0 ${selectedImage === idx ? 'border-purple-600 scale-95' : 'border-transparent'}`}>
                  <img src={img} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Product Configurations Block */}
        <div className="flex flex-col justify-between">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-gray-900 dark:text-white mb-4">{product.name}</h1>
            <div className="flex items-center gap-4 mb-6">
              <div className="flex items-center gap-1 bg-amber-50 dark:bg-amber-950/30 px-3 py-1 rounded-xl text-amber-700 dark:text-amber-400 font-bold">
                <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                {Number(product.average_rating || 0).toFixed(1)}
              </div>
              <span className="text-gray-500 dark:text-gray-400 text-sm">({product.review_count || 0} reviews)</span>
            </div>

            <div className="flex items-baseline gap-4 mb-6">
              <span className="text-4xl font-black text-purple-600">₦{Number(product.price).toLocaleString()}</span>
              {product.compare_at_price && (
                <span className="text-xl text-gray-400 dark:text-gray-500 line-through">₦{Number(product.compare_at_price).toLocaleString()}</span>
              )}
            </div>

            <p className="text-gray-600 dark:text-gray-400 leading-relaxed mb-8">{product.short_description || product.description}</p>
          </div>

          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center border border-gray-200 dark:border-gray-700 rounded-2xl bg-gray-50 dark:bg-gray-800/50">
                <button onClick={() => setQuantity(q => Math.max(1, q - 1))} className="p-3 hover:text-purple-600"><Minus className="w-4 h-4" /></button>
                <span className="w-12 text-center font-bold">{quantity}</span>
                <button onClick={() => setQuantity(q => q + 1)} className="p-3 hover:text-purple-600"><Plus className="w-4 h-4" /></button>
              </div>

              <button onClick={handleAddToCart} disabled={isAddingToCart} className="flex-1 bg-purple-600 hover:bg-purple-700 text-white font-bold py-4 rounded-2xl transition-colors shadow-lg shadow-purple-600/20 disabled:opacity-50">
                {isAddingToCart ? 'Adding...' : 'Add to Cart'}
              </button>
            </div>

            {/* Values Metrics Info */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-gray-100 dark:border-gray-800">
              <div className="flex items-center gap-3"><Truck className="w-5 h-5 text-purple-500" /><div className="text-xs font-semibold">Secure Escrow Logistics</div></div>
              <div className="flex items-center gap-3"><Shield className="w-5 h-5 text-purple-500" /><div className="text-xs font-semibold">Payuee Verification</div></div>
              <div className="flex items-center gap-3"><RotateCcw className="w-5 h-5 text-purple-500" /><div className="text-xs font-semibold">Protected Escrow Window</div></div>
            </div>
          </div>
        </div>
      </div>

      {/* Product Details Tabs section */}
      <div className="mb-16">
        <div className="flex border-b border-gray-200 dark:border-gray-700 gap-8 mb-8">
          {(['description', 'specifications', 'reviews'] as const).map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)} className={`pb-4 text-lg font-bold capitalize border-b-2 transition-colors ${activeTab === tab ? 'border-purple-600 text-purple-600' : 'border-transparent text-gray-500'}`}>
              {tab}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {activeTab === 'description' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="prose dark:prose-invert max-w-none">
              <p className="whitespace-pre-line text-gray-600 dark:text-gray-400">{product.description}</p>
            </motion.div>
          )}

          {activeTab === 'specifications' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="max-w-2xl">
              {Object.keys(specifications).length > 0 ? (
                <div className="border border-gray-100 dark:border-gray-800 rounded-2xl overflow-hidden">
                  {Object.entries(specifications).map(([key, value]: any, idx) => (
                    <div key={key} className={`grid grid-cols-2 p-4 text-sm ${idx % 2 === 0 ? 'bg-gray-50/50 dark:bg-gray-800/20' : 'bg-transparent'}`}>
                      <span className="font-bold text-gray-500 capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-gray-900 dark:text-white font-medium">{value}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No special specifications attached to this item catalog parameters.</p>
              )}
            </motion.div>
          )}

          {activeTab === 'reviews' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                  Customer Reviews {product?.review_count ? `(${product.review_count})` : ''}
                </h3>
                {isAuthenticated && !showReviewForm && (
                  <button
                    onClick={() => setShowReviewForm(true)}
                    className="text-sm font-semibold text-purple-600 hover:text-purple-700"
                  >
                    Write a review
                  </button>
                )}
              </div>

              {showReviewForm && (
                <form
                  onSubmit={handleSubmitReview}
                  className="mb-8 p-6 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-gray-200 dark:border-gray-700 space-y-4"
                >
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Your Rating</label>
                    <div className="flex gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setReviewRating(star)}
                          onMouseEnter={() => setReviewHoverRating(star)}
                          onMouseLeave={() => setReviewHoverRating(0)}
                        >
                          <Star
                            className={`w-7 h-7 ${
                              star <= (reviewHoverRating || reviewRating)
                                ? 'fill-yellow-400 text-yellow-400'
                                : 'text-gray-300 dark:text-gray-600'
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Title (optional)</label>
                    <input
                      type="text"
                      value={reviewTitle}
                      onChange={(e) => setReviewTitle(e.target.value)}
                      maxLength={200}
                      className="w-full px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Your Review</label>
                    <textarea
                      value={reviewComment}
                      onChange={(e) => setReviewComment(e.target.value)}
                      rows={4}
                      required
                      className="w-full px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <div className="flex gap-3">
                    <button
                      type="submit"
                      disabled={isSubmittingReview}
                      className="px-5 py-2.5 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 disabled:opacity-50"
                    >
                      {isSubmittingReview ? 'Submitting...' : 'Submit Review'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowReviewForm(false)}
                      className="px-5 py-2.5 text-gray-600 dark:text-gray-300 font-medium"
                    >
                      Cancel
                    </button>
                  </div>
                  <p className="text-xs text-gray-400">
                    Reviews can only be left on products from orders that have been delivered to you.
                  </p>
                </form>
              )}

              {reviews.length > 0 ? (
                <div className="space-y-6">
                  {reviews.map((review: any) => (
                    <div key={review.id} className="pb-6 border-b border-gray-100 dark:border-gray-800 last:border-0">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center font-semibold text-purple-600">
                          {review.user_name?.[0]?.toUpperCase() || '?'}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-gray-900 dark:text-white text-sm">{review.user_name}</span>
                            {review.is_verified_purchase && (
                              <span className="text-xs font-medium text-green-600 bg-green-50 dark:bg-green-900/20 px-2 py-0.5 rounded-full">
                                Verified Purchase
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1 mt-0.5">
                            {[1, 2, 3, 4, 5].map((star) => (
                              <Star
                                key={star}
                                className={`w-3.5 h-3.5 ${
                                  star <= review.rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300 dark:text-gray-600'
                                }`}
                              />
                            ))}
                          </div>
                        </div>
                      </div>
                      {review.title && <p className="font-medium text-gray-900 dark:text-white mb-1">{review.title}</p>}
                      <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{review.comment}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/30 rounded-3xl border-2 border-dashed border-gray-200 dark:border-gray-700">
                  <MessageSquare className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400 font-medium">No customer review listings verified yet.</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Related Products Fallback List section wrapper */}
      {product?.related_products && product.related_products.length > 0 && (
        <div className="pt-12 border-t border-gray-100 dark:border-gray-800">
          <h2 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight mb-8">You May Also Like</h2>
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
