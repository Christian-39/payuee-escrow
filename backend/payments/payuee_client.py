"""
Payuee API Client for escrow integration.
"""

import hmac
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, List
import requests
from django.conf import settings

logger = logging.getLogger('payuee')


class PayueeClient:
    """Client for Payuee Escrow API."""

    def __init__(self):
        self.api_key = settings.PAYUEE_API_KEY
        self.api_secret = settings.PAYUEE_API_SECRET
        self.base_url = getattr(settings, 'PAYUEE_BASE_URL', 'https://escrow.payuee.com')
        self.base_url = self.base_url.rstrip('/')

        if not all([self.api_key, self.api_secret, self.base_url]):
            raise ValueError("Payuee API credentials not configured properly")

        logger.info(f"PayueeClient initialized with base_url: {self.base_url}")

    def generate_signature(
        self,
        method: str,
        path: str,
        body: str = '',
        timestamp: Optional[str] = None
    ) -> tuple:
        """Generate HMAC SHA256 signature."""
        if timestamp is None:
            timestamp = str(int(time.time()))

        payload = f"{timestamp}{method.upper()}{path}{body}"

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature, timestamp

    def verify_webhook_signature(
        self,
        signature: str,
        timestamp: str,
        method: str,
        path: str,
        body: str = ''
    ) -> bool:
        """Verify incoming webhook signature from Payuee."""
        expected_sig, _ = self.generate_signature(method, path, body, timestamp)
        return hmac.compare_digest(signature, expected_sig)

    def make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        idempotency_key: Optional[str] = None,
        retries: int = 2
    ) -> Dict[str, Any]:
        """Make authenticated request to Payuee API."""
        if not path.startswith('/'):
            path = '/' + path

        # Separate sign_path from query params
        if '?' in path:
            sign_path, query_string = path.split('?', 1)
            url = f"{self.base_url}{sign_path}?{query_string}"
        else:
            sign_path = path
            url = f"{self.base_url}{path}"

        if data:
            body = json.dumps(data, separators=(',', ':'), sort_keys=True)
        else:
            body = ''

        # Sign using base path ONLY (no query params)
        signature, timestamp = self.generate_signature(method, sign_path, body)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_secret}',
            'X-Payuee-Public-Key': self.api_key,
            'X-Payuee-Signature': signature,
            'X-Payuee-Timestamp': timestamp,
        }

        if idempotency_key and method.upper() == 'POST':
            headers['X-Payuee-Idempotency-Key'] = idempotency_key

        logger.info(f"Payuee API Request: {method} {url}")

        for attempt in range(retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=body if body else None,
                    timeout=15,
                )

                logger.info(f"Payuee API Response: {response.status_code}")

                if response.status_code in [200, 201]:
                    return {'success': True, 'data': response.json()}
                elif response.status_code == 401:
                    return {'success': False, 'error': 'Authentication failed', 'status_code': 401}
                elif response.status_code == 405:
                    allow_header = response.headers.get('Allow', 'Not specified')
                    return {
                        'success': False,
                        'error': f'Method Not Allowed. Allowed: {allow_header}',
                        'status_code': 405
                    }
                else:
                    raw_content = response.content.decode('utf-8') if response.content else ''
                    try:
                        error_data = response.json()
                    except:
                        error_data = {'message': raw_content or 'Unknown error'}

                    logger.error(f"PAYUEE ERROR ({response.status_code}): {raw_content[:500]}")

                    return {
                        'success': False,
                        'error': error_data.get('message', error_data.get('error', 'Unknown error')),
                        'status_code': response.status_code,
                        'raw_response': raw_content,
                    }

            except Exception as e:
                logger.error(f"Request exception on attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Max retries exceeded'}

    # ─────────────────────────────────────────────────────────────
    # PRODUCTS (with /v1 prefix)
    # ─────────────────────────────────────────────────────────────

    def get_store_products(self, **kwargs) -> Dict[str, Any]:
        """Fetch products from Payuee store."""
        data = {
            "category": kwargs.get('category', 'all'),
            "user_lat": kwargs.get('user_lat', 6.5244),
            "user_lon": kwargs.get('user_lon', 3.3792),
            "max_distance": kwargs.get('max_distance', 100),
            "min_price": kwargs.get('min_price', 0),
            "max_price": kwargs.get('max_price', 100000),
            "min_weight": kwargs.get('min_weight', 0),
            "max_weight": kwargs.get('max_weight', 50),
            "page_number": kwargs.get('page_number', 1),
            "sort_option": kwargs.get('sort_option', 7),
        }
        if 'tags' in kwargs:
            data['tags'] = kwargs['tags']

        result = self.make_request('POST', '/v1/products', data)
        
        if not result.get('success') and result.get('status_code') == 405:
            import urllib.parse
            query_string = urllib.parse.urlencode(data)
            path = f'/v1/products?{query_string}'
            result = self.make_request('GET', path, data=None)

        return result

    def get_all_store_products(self, max_pages=5, **kwargs) -> Dict[str, Any]:
        """Fetch multiple pages of products."""
        all_products = []
        page = 1

        while page <= max_pages:
            result = self.get_store_products(page_number=page, **kwargs)
            if not result.get('success'):
                break

            data = result.get('data', {})
            products = data.get('success', [])
            all_products.extend(products)

            pagination = data.get('pagination', {})
            if pagination.get('NextPage', 0) <= 0 or page >= pagination.get('TotalPages', 1):
                break
            page += 1

        return {'success': True, 'data': {'success': all_products}}

    def search_products(self, **kwargs) -> Dict[str, Any]:
        """Search products with advanced filters."""
        data = {
            "search_term": kwargs.get('search_term', ''),
            "limit": max(int(kwargs.get('limit', 100)), 100),
            "category": kwargs.get('category', 'all'),
            "min_price": kwargs.get('min_price', 0.0),
            "max_price": kwargs.get('max_price', 100000.0),
            "min_weight": kwargs.get('min_weight', 0.5),
            "max_weight": kwargs.get('max_weight', 100.0),
            "page_number": kwargs.get('page_number', 1),
            "sort_option": kwargs.get('sort_option', 7),
        }
        if 'tags' in kwargs:
            data['tags'] = kwargs['tags']
        return self.make_request('POST', '/v1/products/search', data)

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get single product by ID."""
        return self.make_request('GET', f'/v1/products/{product_id}')

    # ─────────────────────────────────────────────────────────────
    # WALLET
    # ─────────────────────────────────────────────────────────────

    def get_wallet_balance(self) -> Dict[str, Any]:
        return self.make_request('GET', '/v1/wallet/balance')

    def get_wallet_funding_details(self) -> Dict[str, Any]:
        return self.make_request('GET', '/v1/wallet/fund')

    # ─────────────────────────────────────────────────────────────
    # LOCATION
    # ─────────────────────────────────────────────────────────────

    def get_states(self) -> Dict[str, Any]:
        return self.make_request('GET', '/v1/location/states')

    def get_cities(self, state: str) -> Dict[str, Any]:
        encoded_state = requests.utils.quote(state)
        return self.make_request('GET', f'/v1/location/cities?state={encoded_state}')

    # ─────────────────────────────────────────────────────────────
    # LOGISTICS
    # ─────────────────────────────────────────────────────────────

    def get_shipping_fees(self, **kwargs) -> Dict[str, Any]:
        data = {
            "vendors": kwargs['vendors'],
            "state": kwargs['state'],
            "city": kwargs['city'],
            "latitude": kwargs['latitude'],
            "longitude": kwargs['longitude'],
            "cart_items": kwargs['cart_items'],
        }
        return self.make_request('POST', '/v1/order/shipping-fees', data)

    # ─────────────────────────────────────────────────────────────
    # ORDERS
    # ─────────────────────────────────────────────────────────────

    def create_order(self, trans_code, webhook_response_url, customer, cart_items, shipping, idempotency_key=None):
        if not idempotency_key:
            raise ValueError("idempotency_key is required")

        import re
        if not trans_code or not re.match(r'^\d{6}$', str(trans_code)):
            raise ValueError("trans_code must be exactly 6 digits")

        validated_cart_items = []
        for item in cart_items:
            validated_item = {
                "product_id": item['product_id'],
                "cart_meta": {
                    "quantity": item.get('quantity', item.get('cart_meta', {}).get('quantity', 1)),
                }
            }
            outfit_size = item.get('outfit_size') or item.get('cart_meta', {}).get('outfit_size')
            if outfit_size:
                validated_item['cart_meta']['outfit_size'] = outfit_size
            validated_cart_items.append(validated_item)

        data = {
            "trans_code": str(trans_code),
            "webhook_response_url": webhook_response_url,
            "customer": customer,
            "cart_items": validated_cart_items,
            "shipping": shipping,
        }
        return self.make_request('POST', '/v1/order/create', data, idempotency_key=idempotency_key)

    def get_order(self, order_id: int) -> Dict[str, Any]:
        return self.make_request('GET', f'/v1/order/{order_id}')

    def list_orders(self, page: int = 1, limit: int = 15) -> Dict[str, Any]:
        return self.make_request('GET', f'/v1/order/list?page={page}&limit={limit}')

    def scan_qr(self, encrypted_payload: str) -> Dict[str, Any]:
        return self.make_request('POST', '/v1/order/scan-qr', {"encrypted": encrypted_payload})

    def verify_order(self, encrypted: str, customer_id: int, trans_code: str) -> Dict[str, Any]:
        return self.make_request('POST', '/v1/order/verify', {
            "encrypted": encrypted,
            "customer_id": customer_id,
            "trans_code": trans_code,
        })

    def report_order(self, order_id: int, report_note: str) -> Dict[str, Any]:
        return self.make_request('POST', '/v1/order/report', {
            "order_id": order_id,
            "report_note": report_note,
        })

    def cancel_order(self, order_id: int, trans_code: str, report_note: str = '') -> Dict[str, Any]:
        data = {
            "order_id": order_id,
            "trans_code": trans_code,
        }
        if report_note:
            data['report_note'] = report_note
        return self.make_request('POST', '/v1/order/cancel', data)


_payuee_client = None

def get_payuee_client() -> PayueeClient:
    global _payuee_client
    if _payuee_client is None:
        _payuee_client = PayueeClient()
    return _payuee_client
