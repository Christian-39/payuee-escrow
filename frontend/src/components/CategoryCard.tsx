/**
 * Category Card Component
 */

import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { Category } from '../types';

interface CategoryCardProps {
  category: Category;
}
const BASE_URL = "http://127.0.0.1:8000";
export default function CategoryCard({ category }: CategoryCardProps) {
  return (
    <Link to={`/products?category=${category.slug}`}>
      <motion.div
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className="group relative aspect-square rounded-2xl overflow-hidden bg-gray-100 dark:bg-gray-700 shadow-sm hover:shadow-lg transition-all duration-300"
      >
        {/* Background Image */}
        {category.image ? (
          <img
            src={
              category.image?.startsWith('http')
              ? category.image
              : `${BASE_URL}${category.image}`
            }
            alt={category.name}
            className="absolute inset-0 w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
            loading="lazy"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500 to-indigo-600" />
        )}
        
        {/* Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
        
        {/* Content */}
        <div className="absolute inset-0 flex flex-col justify-end p-4">
          <h3 className="text-lg font-bold text-white mb-1">
            {category.name}
          </h3>
          <p className="text-sm text-white/80">
            {category.product_count} products
          </p>
        </div>
      </motion.div>
    </Link>
  );
}
