# gadgethub/urls.py
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

def api_root(request):
    return JsonResponse({
        "status": "ok",
        "message": "GadgetHub API is running",
        "version": "1.0.0"
    })

urlpatterns = [
    path("", api_root, name="api-root"),  # Add this line
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/admin/', include('admin_dashboard.urls')),
    path('api/webhooks/', include('payments.webhook_urls')),
]