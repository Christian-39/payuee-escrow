"""
URL configuration for webhooks.
"""

from django.urls import path
from .webhooks import payuee_webhook

urlpatterns = [
    path('payuee/', payuee_webhook, name='payuee_webhook'),
]
