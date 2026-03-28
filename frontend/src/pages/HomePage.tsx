/**
 * Home Page - Featured Products, Categories, Hero Section
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Zap, Shield, Truck, Headphones } from 'lucide-react';
import api from '../lib/api';
import type { ProductListItem, Category } from '../types';
import ProductCard from '../components/ProductCard';
import CategoryCard from '../components/CategoryCard';
import { toast } from 'sonner';

const features = [
  {
    icon: Zap,
    title: 'Fast Delivery',
    description: 'Get your gadgets delivered within 24-48 hours',
  },
  {
    icon: Shield,
    title: 'Secure Payment',
    description: 'Your payments are protected by Payuee escrow',
  },
  {
    icon: Truck,
    title: 'Free Shipping',
    description: 'Free shipping on orders over $100',
  },
  {
    icon: Headphones,
    title: '24/7 Support',
    description: 'Round the clock customer support',
  },
];

export default function HomePage() {
  const [featuredProducts, setFeaturedProducts] = useState<ProductListItem[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchHomeData();
  }, []);

  const fetchHomeData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch featured products and categories in parallel
      const [productsRes, categoriesRes] = await Promise.all([
        api.get('/products/featured/'),
        api.get('/products/categories/'),
      ]);
      
      setFeaturedProducts(productsRes.data.results || productsRes.data);
      setCategories(categoriesRes.data.results || []);
    } catch (error) {
      toast.error('Failed to load home page data');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800">
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=1920&q=80')] bg-cover bg-center opacity-20" />
        <div className="absolute inset-0 bg-gradient-to-r from-purple-900/80 to-transparent" />
        
        <div className="relative px-6 py-16 lg:px-16 lg:py-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-2xl"
          >
            <span className="inline-block px-4 py-2 mb-6 text-sm font-semibold text-purple-600 bg-white rounded-full">
              New Collection 2024
            </span>
            <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
              Discover the Future of{' '}
              <span className="text-yellow-400">Technology</span>
            </h1>
            <p className="text-lg text-purple-100 mb-8 max-w-lg">
              Shop the latest gadgets, electronics, and accessories. 
              Secure payments with Payuee escrow protection.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                to="/products"
                className="inline-flex items-center gap-2 px-8 py-4 bg-white text-purple-600 font-semibold rounded-xl hover:bg-gray-100 transition-colors"
              >
                Shop Now
                <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                to="/search"
                className="inline-flex items-center gap-2 px-8 py-4 bg-purple-500/30 text-white font-semibold rounded-xl hover:bg-purple-500/40 transition-colors backdrop-blur-sm"
              >
                Explore
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {features.map((feature, index) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
            className="flex items-start gap-4 p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-xl">
              <feature.icon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                {feature.title}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {feature.description}
              </p>
            </div>
          </motion.div>
        ))}
      </section>

      {/* Categories Section */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Shop by Category
          </h2>
          <Link
            to="/products"
            className="text-purple-600 hover:text-purple-700 font-medium flex items-center gap-1"
          >
            View All
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-2xl animate-pulse"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {categories.map((category, index) => (
              <motion.div
                key={category.id}
                initial={{ opacity: 0, scale: 0.9 }} 
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <CategoryCard category={category} />
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* Featured Products Section */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Featured Products
          </h2>
          <Link
            to="/products?featured=true"
            className="text-purple-600 hover:text-purple-700 font-medium flex items-center gap-1"
          >
            View All
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="aspect-[3/4] bg-gray-200 dark:bg-gray-700 rounded-2xl animate-pulse"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredProducts.map((product, index) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.05 }}
              >
                <ProductCard product={product} />
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* CTA Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gray-900">
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1468495244123-6c6c332eeece?w=1920&q=80')] bg-cover bg-center opacity-30" />
        <div className="relative px-6 py-16 lg:px-16 lg:py-20 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
              Join Our Newsletter
            </h2>
            <p className="text-gray-300 mb-8 max-w-lg mx-auto">
              Subscribe to get exclusive offers, new arrivals, and tech news 
              delivered to your inbox.
            </p>
            <form className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-6 py-4 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <button
                type="submit"
                className="px-8 py-4 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors"
              >
                Subscribe
              </button>
            </form>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
