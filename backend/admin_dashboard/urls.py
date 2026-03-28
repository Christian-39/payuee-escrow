from django.urls import path
from .views import (
    dashboard_stats,
    sales_chart_data,
    top_products,
    recent_orders,
    inventory_status,
    update_inventory,
    UserListView,
    user_detail,
    toggle_user_status,
)
# Import order admin views from orders app
from orders.views import (
    AdminOrderListView,
    AdminOrderDetailView,
    AdminOrderStatusUpdateView,
    AdminShippingUpdateView,
    verify_order_delivery,
)

urlpatterns = [
    # Dashboard
    path('stats/', dashboard_stats, name='dashboard_stats'),
    path('charts/sales/', sales_chart_data, name='sales_chart_data'),
    path('top-products/', top_products, name='top_products'),
    path('recent-orders/', recent_orders, name='recent_orders'),
    
    # Inventory
    path('inventory/status/', inventory_status, name='inventory_status'),
    path('inventory/update/<uuid:product_id>/', update_inventory, name='update_inventory'),
    
    # Users
    path('users/', UserListView.as_view(), name='admin_user_list'),
    path('users/<uuid:user_id>/', user_detail, name='admin_user_detail'),
    path('users/<uuid:user_id>/toggle-status/', toggle_user_status, name='toggle_user_status'),
    
    # Orders (now under /api/admin/orders/)
    path('orders/', AdminOrderListView.as_view(), name='admin_order_list'),
    path('orders/<str:order_number>/', AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('orders/<str:order_number>/status/', AdminOrderStatusUpdateView.as_view(), name='admin_order_status'),
    path('orders/<str:order_number>/shipping/', AdminShippingUpdateView.as_view(), name='admin_shipping_update'),
    path('orders/<str:order_number>/verify/', verify_order_delivery, name='verify_delivery'),
]