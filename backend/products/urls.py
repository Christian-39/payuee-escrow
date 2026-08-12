"""
URL configuration for the products app.
"""

from django.urls import path
from .views import (
    CategoryListView,
    CategoryDetailView,
    ProductListView,
    ProductDetailView,
    FeaturedProductsView,
    RelatedProductsView,
    search_products,
    WishlistListView,
    WishlistAddView,
    WishlistRemoveView,
    toggle_wishlist,
    get_wishlist_count,
    get_reviews_count,
    ProductReviewListView,
    ProductReviewCreateView,
    AdminProductListCreateView,
    AdminProductDetailView,
    get_categories_with_products
)

urlpatterns = [
    # Categories
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/with-products/', get_categories_with_products, name='categories_with_products'),
    path('categories/<str:slug>/', CategoryDetailView.as_view(), name='category_detail'),
      
    # Wishlist
    path('wishlist/', WishlistListView.as_view(), name='wishlist_list'),
    path('wishlist/add/', WishlistAddView.as_view(), name='wishlist_add'),
    path('wishlist/remove/<uuid:product_id>/', WishlistRemoveView.as_view(), name='wishlist_remove'),
    path('wishlist/toggle/<uuid:product_id>/', toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/count/', get_wishlist_count, name='wishlist_count'),

    # Reviews (global, must come before the <str:slug>/ catch-all below)
    path('reviews/count/', get_reviews_count, name='reviews_count'),

    # Products
    path('', ProductListView.as_view(), name='product_list'),
    path('featured/', FeaturedProductsView.as_view(), name='featured_products'),
    path('search/', search_products, name='product_search'),
    path('<str:slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('<str:slug>/related/', RelatedProductsView.as_view(), name='related_products'),
    
    # Per-product reviews
    path('<str:slug>/reviews/', ProductReviewListView.as_view(), name='product_reviews'),
    path('<str:slug>/reviews/create/', ProductReviewCreateView.as_view(), name='create_review'),

    # Admin
    path('admin/products/', AdminProductListCreateView.as_view(), name='admin_product_list_create'),
    path('admin/products/<uuid:id>/', AdminProductDetailView.as_view(), name='admin_product_detail'),
]
