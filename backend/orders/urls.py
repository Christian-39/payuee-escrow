"""
URL configuration for the orders app.
"""

from django.urls import path
from .views import (
    # Cart views
    CartView,
    AddToCartView,
    UpdateCartItemView,
    RemoveFromCartView,
    ClearCartView,
    # Order views
    OrderListView,
    OrderDetailView,
    OrderTrackingView,
    checkout,
    get_order_summary,
    get_orders_count,
    cancel_order,
    report_order,
    # Admin views
    AdminOrderListView,
    AdminOrderDetailView,
    AdminOrderStatusUpdateView,
    AdminShippingUpdateView,
    verify_order_delivery,
)

urlpatterns = [
    # Cart endpoints
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='add_to_cart'),
    path('cart/update/<uuid:item_id>/', UpdateCartItemView.as_view(), name='update_cart_item'),
    path('cart/remove/<uuid:item_id>/', RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('cart/clear/', ClearCartView.as_view(), name='clear_cart'),
    
    # Checkout endpoints
    path('checkout/', checkout, name='checkout'),
    path('checkout/summary/', get_order_summary, name='order_summary'),
    
    # Admin endpoints - MUST come BEFORE the generic order patterns
    path('admin/orders/', AdminOrderListView.as_view(), name='admin_order_list'),
    path('admin/orders/<str:order_number>/', AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('admin/orders/<str:order_number>/status/', AdminOrderStatusUpdateView.as_view(), name='admin_order_status'),
    path('admin/orders/<str:order_number>/shipping/', AdminShippingUpdateView.as_view(), name='admin_shipping_update'),
    path('admin/orders/<str:order_number>/verify/', verify_order_delivery, name='verify_delivery'),
    
    # User order endpoints - MUST come AFTER admin patterns
    path('', OrderListView.as_view(), name='order_list'),
    path('count/', get_orders_count, name='orders-count'),
    path('<str:order_number>/', OrderDetailView.as_view(), name='order_detail'),
    path('<str:order_number>/track/', OrderTrackingView.as_view(), name='order_tracking'),
    path('<str:order_number>/cancel/', cancel_order, name='cancel_order'),
    path('<str:order_number>/report/', report_order, name='report_order'),
]