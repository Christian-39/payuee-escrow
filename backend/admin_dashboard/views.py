"""
Views for the admin dashboard.
Handles analytics, user management, and inventory.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q
from django.db.models import F
from django.utils import timezone
from datetime import timedelta, datetime

from accounts.models import User
from products.models import Product, Category, ProductView
from orders.models import Order, OrderItem
from payments.models import Transaction


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def dashboard_stats(request):
    """Get dashboard statistics."""
    
    # Date ranges
    today = timezone.now()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Sales stats
    total_sales = Order.objects.filter(
        status__in=['delivered', 'confirmed', 'shipped']
    ).aggregate(total=Sum('total'))['total'] or 0
    
    sales_30_days = Order.objects.filter(
        created_at__gte=last_30_days,
        status__in=['delivered', 'confirmed', 'shipped']
    ).aggregate(total=Sum('total'))['total'] or 0
    
    sales_7_days = Order.objects.filter(
        created_at__gte=last_7_days,
        status__in=['delivered', 'confirmed', 'shipped']
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Order stats
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    processing_orders = Order.objects.filter(status='processing').count()
    shipped_orders = Order.objects.filter(shipping_status='shipped').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    
    # Customer stats
    total_customers = User.objects.filter(is_admin=False).count()
    new_customers_30_days = User.objects.filter(
        created_at__gte=last_30_days,
        is_admin=False
    ).count()
    
    # Product stats
    total_products = Product.objects.count()
    active_products = Product.objects.filter(status='active').count()
    low_stock_products = Product.objects.filter(
        track_inventory=True,
        quantity__lte=F('low_stock_threshold'),
        quantity__gt=0
    ).count()
    out_of_stock_products = Product.objects.filter(
        track_inventory=True,
        quantity=0
    ).count()
    
    # Revenue stats
    total_revenue = Order.objects.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total'))['total'] or 0
    
    pending_revenue = Order.objects.filter(
        payment_status='pending',
        status__in=['pending', 'confirmed', 'processing']
    ).aggregate(total=Sum('total'))['total'] or 0
    
    return Response({
        'sales': {
            'total': total_sales,
            'last_30_days': sales_30_days,
            'last_7_days': sales_7_days,
        },
        'orders': {
            'total': total_orders,
            'pending': pending_orders,
            'processing': processing_orders,
            'shipped': shipped_orders,
            'delivered': delivered_orders,
        },
        'customers': {
            'total': total_customers,
            'new_last_30_days': new_customers_30_days,
        },
        'products': {
            'total': total_products,
            'active': active_products,
            'low_stock': low_stock_products,
            'out_of_stock': out_of_stock_products,
        },
        'revenue': {
            'total': total_revenue,
            'pending': pending_revenue,
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def sales_chart_data(request):
    """Get sales data for charts."""
    
    period = request.query_params.get('period', '30')
    days = int(period)
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Generate date range
    dates = []
    sales_data = []
    orders_data = []
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
        
        # Get sales for this date
        daily_sales = Order.objects.filter(
            created_at__date=date,
            status__in=['delivered', 'confirmed', 'shipped']
        ).aggregate(total=Sum('total'))['total'] or 0
        sales_data.append(float(daily_sales))
        
        # Get orders count for this date
        daily_orders = Order.objects.filter(
            created_at__date=date
        ).count()
        orders_data.append(daily_orders)
    
    return Response({
        'labels': dates,
        'sales': sales_data,
        'orders': orders_data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def top_products(request):
    """Get top selling products."""
    
    limit = int(request.query_params.get('limit', 10))
    
    top_products = OrderItem.objects.values(
        'product__id',
        'product__name',
        'product__featured_image'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_sold')[:limit]
    
    return Response(list(top_products))


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def recent_orders(request):
    """Get recent orders."""
    
    limit = int(request.query_params.get('limit', 10))
    
    orders = Order.objects.select_related('user').order_by('-created_at')[:limit]
    
    data = []
    for order in orders:
        data.append({
            'id': str(order.id),
            'order_number': order.order_number,
            'customer': order.user.full_name or order.user.email,
            'total': order.total,
            'status': order.status,
            'payment_status': order.payment_status,
            'created_at': order.created_at
        })
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def inventory_status(request):
    """Get inventory status."""
    
    # Low stock products
    low_stock = Product.objects.filter(
        track_inventory=True,
        quantity__lte=F('low_stock_threshold'),
        quantity__gt=0
    ).values('id', 'name', 'sku', 'quantity', 'low_stock_threshold')
    
    # Out of stock products
    out_of_stock = Product.objects.filter(
        track_inventory=True,
        quantity=0
    ).values('id', 'name', 'sku')
    
    return Response({
        'low_stock': list(low_stock),
        'out_of_stock': list(out_of_stock),
        'low_stock_count': low_stock.count(),
        'out_of_stock_count': out_of_stock.count()
    })


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def update_inventory(request, product_id):
    """Update product inventory."""
    
    from products.models import Product
    from rest_framework.generics import get_object_or_404
    
    product = get_object_or_404(Product, id=product_id)
    
    quantity = request.data.get('quantity')
    if quantity is None:
        return Response(
            {'error': 'Quantity is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        quantity = int(quantity)
        if quantity < 0:
            return Response(
                {'error': 'Quantity cannot be negative.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError:
        return Response(
            {'error': 'Quantity must be a number.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    old_quantity = product.quantity
    product.quantity = quantity
    product.save()
    
    return Response({
        'message': 'Inventory updated successfully.',
        'product': {
            'id': str(product.id),
            'name': product.name,
            'old_quantity': old_quantity,
            'new_quantity': quantity
        }
    })


# User Management
class UserListView(generics.ListAPIView):
    """Admin: List all users."""
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return User.objects.all().order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Filter by role
        role = request.query_params.get('role')
        if role == 'admin':
            queryset = queryset.filter(is_admin=True)
        elif role == 'customer':
            queryset = queryset.filter(is_admin=False)
        
        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            data = []
            for user in page:
                data.append({
                    'id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                    'phone_number': user.phone_number,
                    'is_admin': user.is_admin,
                    'is_active': user.is_active,
                    'email_verified': user.email_verified,
                    'created_at': user.created_at,
                    'order_count': user.orders.count()
                })
            return self.get_paginated_response(data)
        
        data = []
        for user in queryset:
            data.append({
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'phone_number': user.phone_number,
                'is_admin': user.is_admin,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'created_at': user.created_at,
                'order_count': user.orders.count()
            })
        
        return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def user_detail(request, user_id):
    """Admin: Get user details."""
    
    from rest_framework.generics import get_object_or_404
    
    user = get_object_or_404(User, id=user_id)
    
    # Get user's orders
    orders = Order.objects.filter(user=user).order_by('-created_at')[:10]
    orders_data = []
    for order in orders:
        orders_data.append({
            'order_number': order.order_number,
            'total': order.total,
            'status': order.status,
            'created_at': order.created_at
        })
    
    return Response({
        'id': str(user.id),
        'email': user.email,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'phone_number': user.phone_number,
        'address': user.address,
        'city': user.city,
        'state': user.state,
        'country': user.country,
        'postal_code': user.postal_code,
        'profile_image': user.profile_image,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
        'email_verified': user.email_verified,
        'created_at': user.created_at,
        'orders': orders_data,
        'total_orders': user.orders.count(),
        'total_spent': user.orders.filter(
            status__in=['delivered', 'confirmed']
        ).aggregate(total=Sum('total'))['total'] or 0
    })


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def toggle_user_status(request, user_id):
    """Admin: Toggle user active status."""
    
    from rest_framework.generics import get_object_or_404
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deactivating yourself
    if user == request.user:
        return Response(
            {'error': 'You cannot deactivate your own account.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user.is_active = not user.is_active
    user.save()
    
    return Response({
        'message': f"User {'activated' if user.is_active else 'deactivated'} successfully.",
        'is_active': user.is_active
    })