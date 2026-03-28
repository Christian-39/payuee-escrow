/**
 * Type Definitions
 */

// User Types
export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone_number: string | null;
  profile_image: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  dark_mode: boolean;
  email_notifications: boolean;
  push_notifications: boolean;
  marketing_emails: boolean;
  is_admin: boolean;
  email_verified: boolean;
  has_complete_profile: boolean;
  created_at: string;
  updated_at: string;
}

// Category Types
export interface Category {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image: string | null;
  parent: string | null;
  subcategories: Category[];
  product_count: number;
  is_active: boolean;
}

// Product Types
export interface Product {
  id: string;
  name: string;
  slug: string;
  sku: string | null;
  source: 'local' | 'payuee';
  payuee_product_id: string | null;
  description: string;
  short_description: string | null;
  specifications: Record<string, any>;
  price: number;
  compare_at_price: number | null;
  discount_percentage: number;
  currency: string;
  quantity: number;
  is_in_stock: boolean;
  is_low_stock: boolean;
  low_stock_threshold: number;
  featured_image: string;
  images: string[];
  category: Category;
  status: string;
  is_featured: boolean;
  meta_title: string | null;
  meta_description: string | null;
  meta_keywords: string | null;
  average_rating: number;
  review_count: number;
  is_wishlisted: boolean;
  related_products: ProductListItem[];
  created_at: string;
  updated_at: string;
}

export interface ProductListItem {
  id: string;
  name: string;
  slug: string;
  sku: string | null;
  price: number;
  compare_at_price: number | null;
  discount_percentage: number;
  featured_image: string;
  category?: {
    id: string;
    name: string;
    slug: string;
  };
  is_in_stock: boolean;
  average_rating: number;
  review_count: number;
  is_featured: boolean;
  is_wishlisted: boolean;
  created_at: string;
  status: 'active' | 'draft' | 'archived' | string;
}

// Review Types
export interface ProductReview {
  id: string;
  user_name: string;
  user_image: string | null;
  rating: number;
  title: string | null;
  comment: string;
  is_verified_purchase: boolean;
  helpful_count: number;
  created_at: string;
}

// Cart Types
export interface CartItem {
  id: string;
  product: ProductListItem;
  quantity: number;
  total_price: number;
  created_at: string;
}

export interface Cart {
  id: string;
  items: CartItem[];
  total_items: number;
  subtotal: number;
  total: number;
  updated_at: string;
}

// Order Types
export interface OrderItem {
  id: string;
  product_name: string;
  product_sku: string | null;
  product_image: string | null;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface Order {
  id: string;
  order_number: string;
  status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'refunded';
  payment_status: 'pending' | 'paid' | 'failed' | 'refunded';
  shipping_status: 'pending' | 'processing' | 'shipped' | 'delivered';
  payuee_order_id: string | null;
  payuee_escrow_status: string | null;
  subtotal: number;
  shipping_cost: number;
  tax: number;
  discount: number;
  total: number;
  currency: string;
  shipping_name: string;
  shipping_address: string;
  shipping_city: string;
  shipping_state: string;
  shipping_country: string;
  shipping_postal_code: string;
  shipping_phone: string;
  billing_name: string | null;
  billing_address: string | null;
  billing_city: string | null;
  billing_state: string | null;
  billing_country: string | null;
  billing_postal_code: string | null;
  customer_note: string | null;
  admin_note: string | null;
  tracking_number: string | null;
  carrier: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  items: OrderItem[];
  status_history: OrderStatusHistory[];
  created_at: string;
  updated_at: string;
}

export interface OrderListItem {
  id: string;
  order_number: string;
  status: string;
  payment_status: string;
  shipping_status: string;
  total: number;
  currency: string;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrderStatusHistory {
  status: string;
  notes: string | null;
  created_by_name: string | null;
  created_at: string;
}

// Wishlist Types
export interface WishlistItem {
  id: string;
  product: ProductListItem;
  created_at: string;
}

// Dashboard Types
export interface DashboardStats {
  sales: {
    total: number;
    last_30_days: number;
    last_7_days: number;
  };
  orders: {
    total: number;
    pending: number;
    processing: number;
    shipped: number;
    delivered: number;
  };
  customers: {
    total: number;
    new_last_30_days: number;
  };
  products: {
    total: number;
    active: number;
    low_stock: number;
    out_of_stock: number;
  };
  revenue: {
    total: number;
    pending: number;
  };
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
