"""
Payuee API Client for escrow integration.
"""

import hmac
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional
import requests
from django.conf import settings

logger = logging.getLogger('payuee')


class PayueeClient:
    """Client for Payuee Escrow API."""

    def __init__(self):
        self.api_key = settings.PAYUEE_API_KEY
        self.api_secret = settings.PAYUEE_API_SECRET
        self.base_url = getattr(settings, 'PAYUEE_BASE_URL', 'https://escrow.payuee.com')

        if not all([self.api_key, self.api_secret, self.base_url]):
            raise ValueError("Payuee API credentials not configured")

    def generate_signature(
        self,
        method: str,
        path: str,
        body: str = '',
        timestamp: Optional[str] = None
    ) -> tuple:
        """
        Generate HMAC SHA256 signature.
        """
        if timestamp is None:
            timestamp = str(int(time.time()))

        # Include body in signature as per documentation
        payload = f"{timestamp}{method.upper()}{path}{body}"

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature, timestamp

    def make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        idempotency_key: Optional[str] = None,
        retries: int = 2
    ) -> Dict[str, Any]:
        """Make authenticated request to Payuee API."""
        url = f"{self.base_url}{path}"
        
        if data:
            body = json.dumps(data, separators=(',', ':'), sort_keys=True)
        else:
            body = ''

        signature, timestamp = self.generate_signature(method, path, body)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_secret}',
            'X-Payuee-Public-Key': self.api_key,
            'X-Payuee-Signature': signature,
            'X-Payuee-Timestamp': timestamp,
        }

        # Use correct idempotency header name per docs
        if idempotency_key and method.upper() == 'POST':
            headers['X-Payuee-Idempotency-Key'] = idempotency_key

        for attempt in range(retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=body if body else None,
                    timeout=60
                )

                if response.status_code in [200, 201]:
                    return {'success': True, 'data': response.json()}
                elif response.status_code == 401:
                    logger.error(f"Authentication failed: {response.text}")
                    logger.error(f"401 Response body: {response.text}")
                    logger.error(f"401 Response headers: {dict(response.headers)}")
                    return {'success': False, 'error': 'Authentication failed', 'status_code': 401}
                else:
                    # Handle other errors
                    raw_content = response.content.decode('utf-8') if response.content else ''
                    logger.error(f"Raw response content: {raw_content}")
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(f"Response headers: {dict(response.headers)}")

                    try:
                        error_data = response.json()
                    except:
                        error_data = {'message': raw_content or 'Unknown error'}
    
                    logger.error(f"API error: {response.status_code} - {error_data}")
                    return {
                        'success': False,
                        'error': error_data.get('message', error_data.get('error', 'Unknown error')),
                        'status_code': response.status_code
                    }

            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Max retries exceeded'}

    def test_auth(self) -> Dict[str, Any]:
        """Test authentication."""
        return self.make_request('GET', '/v1/auth-status')

    def get_store_products(self) -> Dict[str, Any]:
        """Fetch products from Payuee store."""
        data = {
            "category": "all",  # Valid category from docs
            "user_lat": 6.5244,     # Lagos coordinates (example)
            "user_lon": 3.3792,
            "max_distance": 100,
            "min_price": 0,
            "max_price": 100000,
            "min_weight": 0,
            "max_weight": 50,
            "page_number": 1,
            "sort_option": 7
        }
        return self.make_request('POST', '/v1/products', data)

    def create_order(self, order, cart_items, eshop_id: str) -> Dict[str, Any]:
        """Create order in Payuee escrow system."""
        try:
           # Build products array per API spec
            products = []
            for item in cart_items:
                products.append({
                    'product_id': str(item.product.id),
                    'quantity': item.quantity
                })

            # Match exact API structure from documentation
            data = {
                'eshop_id': eshop_id,
                'products': products,
                'customer_name': (order.user.full_name or order.user.email)[:100],
                'customer_phone': (order.shipping_phone or '')[:20],
                'delivery_address': f"{order.shipping_address}, {order.shipping_city}, {order.shipping_state}, {order.shipping_country}"[:200],
                'reference': order.order_number[:50]
            }

            result = self.make_request(
                'POST',
                '/v1/place-order',
                data,
                idempotency_key=order.idempotency_key
            )

            logger.info(f"Payuee create_order result: {result}")

            if result.get('success'):
                # Note: Adjust based on actual response structure
                order_data = result.get('data', {})
                return {
                    'success': True,
                    'order_id': order_data.get('order_id') or order_data.get('id'),
                    'status': order_data.get('status'),
                    'payment_url': order_data.get('payment_url'),
                    'instructions': order_data.get('payment_instructions')
                }
        
            return {
                'success': False,
                'error': result.get('error', 'Unknown Payuee error'),
                'status_code': result.get('status_code', 400)
            }

        except Exception as e:
            logger.error(f"create_order exception: {e}", exc_info=True)
            raise


# Singleton instance
_payuee_client = None

def get_payuee_client() -> PayueeClient:
    """Get or create Payuee client instance."""
    global _payuee_client
    if _payuee_client is None:
        _payuee_client = PayueeClient()
    return _payuee_client