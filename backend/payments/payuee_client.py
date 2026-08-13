"""
Payuee API Client for escrow integration.

Reference: https://payuee.com/doc/documentation
Base URL:  https://escrow.payuee.com/v1
"""

import hmac
import hashlib
import json
import time
import uuid
import logging
from typing import Dict, Any, Optional, List
import requests
from django.conf import settings

logger = logging.getLogger('payuee')

# Per Payuee docs: retry with exponential backoff on these, never on 4xx.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}


class PayueeClient:
    """Client for the Payuee Escrow API."""

    def __init__(self):
        self.api_key = settings.PAYUEE_API_KEY 
        self.api_secret = settings.PAYUEE_API_SECRET
        self.base_url = getattr(settings, 'PAYUEE_BASE_URL', 'https://escrow.payuee.com')

        if not all([self.api_key, self.api_secret, self.base_url]):
            raise ValueError("Payuee API credentials not configured")

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------
    def generate_signature(
        self,
        method: str,
        path: str,
        body: str = '',
        timestamp: Optional[str] = None
    ) -> tuple:
        """
        Generate the HMAC SHA256 request signature.

        payload = timestamp + UPPERCASE(HTTP_METHOD) + request_path + request_body
        signature = HMAC_SHA256(payload, SecretKey)

        `path` must be the exact request path (e.g. "/v1/products"), never
        including the scheme/host, and must match the path actually requested.
        """
        if timestamp is None:
            timestamp = str(int(time.time()))

        payload = f"{timestamp}{method.upper()}{path}{body}"

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature, timestamp

    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature: str,
        secret: str,
        timestamp: str,
    ) -> bool:
        """
        Verify an inbound Payuee webhook per the documented algorithm:

            signed_payload = timestamp + "." + raw_body
            expected = "sha256=" + HMAC_SHA256(signed_payload, webhook_secret)

        `payload` must be the *raw* request body bytes (not re-serialized JSON),
        and comparison must be constant-time.
        """
        if not signature or not timestamp or not secret:
            return False

        if isinstance(payload, str):
            payload = payload.encode('utf-8')

        signed_payload = timestamp.encode('utf-8') + b'.' + payload
        digest = hmac.new(
            secret.encode('utf-8'),
            signed_payload,
            hashlib.sha256
        ).hexdigest()
        expected = f"sha256={digest}"

        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Core request handling
    # ------------------------------------------------------------------
    def make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        idempotency_key: Optional[str] = None,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"

        body = json.dumps(data, separators=(',', ':'), sort_keys=True) if data else ''

        # Path used for HMAC must NEVER include the query string
        sign_path = path.split('?')[0]

        headers_base = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_secret}',
            'X-Payuee-Public-Key': self.api_key,
        }

        if method.upper() == 'POST':
            headers_base['X-Payuee-Idempotency-Key'] = idempotency_key or str(uuid.uuid4())

        last_error = 'Unknown error'
        last_status = None

        for attempt in range(1, max_attempts + 1):
            # FIXED: use sign_path (no query string) instead of path
            signature, timestamp = self.generate_signature(method, sign_path, body)
            headers = {
                **headers_base,
                'X-Payuee-Signature': signature,
                'X-Payuee-Timestamp': timestamp,
            }

            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=body if body else None,
                    timeout=30,
                )
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                logger.error(f"Payuee network error on {method} {path} (attempt {attempt}): {e}")
                if attempt < max_attempts:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                return {'success': False, 'error': last_error}

            if response.status_code in (200, 201):
                try:
                    return {'success': True, 'data': response.json(), 'status_code': response.status_code}
                except ValueError:
                    return {'success': True, 'data': {}, 'status_code': response.status_code}

            # Parse error body (never log secrets/headers with credentials).
            try:
                error_data = response.json()
            except ValueError:
                error_data = {'message': response.text or 'Unknown error'}

            last_status = response.status_code
            last_error = error_data.get('error', {}).get('message') if isinstance(error_data.get('error'), dict) \
                else error_data.get('message', error_data.get('error', 'Unknown error'))

            logger.error(f"Payuee API error on {method} {path}: {response.status_code} - {last_error}")

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < max_attempts:
                delay = min(1 * (2 ** attempt), 30)
                logger.info(f"Retrying {method} {path} in {delay}s (attempt {attempt + 1}/{max_attempts})")
                time.sleep(delay)
                continue

            # Non-retryable (4xx) or out of attempts.
            return {'success': False, 'error': last_error, 'status_code': last_status}

        return {'success': False, 'error': last_error, 'status_code': last_status}

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    def get_store_products(
        self,
        category: str = 'all',
        page_number: int = 1,
        sort_option: int = 8,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_weight: Optional[float] = None,
        max_weight: Optional[float] = None,
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        max_distance: int = 100,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """POST /v1/products - fetch a page of store products with filters."""
        data = {
            "category": category or 'all',
            "max_distance": max_distance,
            "page_number": page_number,
            "sort_option": sort_option,
        }
        if user_lat is not None:
            data["user_lat"] = user_lat
        if user_lon is not None:
            data["user_lon"] = user_lon
        if min_price is not None:
            data["min_price"] = min_price
        if max_price is not None:
            data["max_price"] = max_price
        if min_weight is not None:
            data["min_weight"] = min_weight
        if max_weight is not None:
            data["max_weight"] = max_weight
        if tags:
            data["tags"] = tags

        return self.make_request('POST', '/v1/products', data)

    def get_all_store_products(
        self,
        max_pages: int = 5,
        category: str = 'all',
        max_distance: int = 10000,
    ) -> Dict[str, Any]:
        all_products: List[Dict] = []
        stores: List[Dict] = []
        page = 1

        while page <= max_pages:
            result = self.get_store_products(
                category=category,
                page_number=page,
                max_distance=max_distance,
            )
            if not result.get('success'):
                if page == 1:
                    return result
                break

            payload = result.get('data', {}) or {}

            # Defensive: API may return null instead of []
            products = payload.get('success') or []
            stores_list = payload.get('stores') or []

            all_products.extend(products)
            stores.extend(stores_list)

            pagination = payload.get('pagination', {}) or {}
            total_pages = pagination.get('TotalPages', page)

            logger.info(
                f"[Payuee] Fetched page {page}/{total_pages}, "
                f"got {len(products)} products, {len(stores_list)} stores"
            )

            if not products or page >= total_pages:
                break
            page += 1

        return {
            'success': True,
            'data': {
                'success': all_products,
                'stores': stores,
            },
        }

    def search_products(
        self,
        search_term: str = '',
        limit: int = 20,
        category: str = 'all',
        page_number: int = 1,
        sort_option: int = 8,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_weight: Optional[float] = None,
        max_weight: Optional[float] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """POST /v1/products/search"""
        data = {
            "search_term": search_term,
            "limit": max(5, min(limit, 50)),
            "category": category or 'all',
            "page_number": page_number,
            "sort_option": sort_option,
        }
        if min_price is not None:
            data["min_price"] = min_price
        if max_price is not None:
            data["max_price"] = max_price
        if min_weight is not None:
            data["min_weight"] = min_weight
        if max_weight is not None:
            data["max_weight"] = max_weight
        if tags:
            data["tags"] = tags

        return self.make_request('POST', '/v1/products/search', data)

    def get_product(self, product_id) -> Dict[str, Any]:
        """
        GET /v1/product/{id}

        NOTE: Payuee's own documentation is internally inconsistent here - the
        prose describes the path as `/v1/product/{id}` (singular) but the
        example curl request hits `/v1/products/{id}` (plural). This client
        uses the documented (singular) path since that's the authoritative
        contract text; if Payuee's live API actually expects the plural form,
        update PRODUCT_DETAIL_PATH below (verify against a real account
        before relying on this in production).
        """
        path = f'/v1/product/{product_id}'
        return self.make_request('GET', path)

    # ------------------------------------------------------------------
    # Wallet
    # ------------------------------------------------------------------
    def get_wallet_balance(self) -> Dict[str, Any]:
        """GET /v1/wallet/balance"""
        return self.make_request('GET', '/v1/wallet/balance')

    def get_wallet_funding_details(self) -> Dict[str, Any]:
        """GET /v1/wallet/fund"""
        return self.make_request('GET', '/v1/wallet/fund')

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------
    def get_states(self) -> Dict[str, Any]:
        """GET /v1/location/states"""
        return self.make_request('GET', '/v1/location/states')

    def get_cities(self, state: str) -> Dict[str, Any]:
        """GET /v1/location/cities?state=..."""
        from urllib.parse import quote
        path = f'/v1/location/cities?state={quote(state)}'
        return self.make_request('GET', path)

    # ------------------------------------------------------------------
    # Shipping
    # ------------------------------------------------------------------
    def calculate_shipping_fees(
        self,
        vendors: List[int],
        state: str,
        city: str,
        latitude: float,
        longitude: float,
        cart_items: List[Dict],
    ) -> Dict[str, Any]:
        """POST /v1/order/shipping-fees"""
        data = {
            "vendors": vendors,
            "state": state,
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
            "cart_items": cart_items,
        }
        return self.make_request('POST', '/v1/order/shipping-fees', data)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def create_order(
        self,
        order,
        cart_items,
        trans_code: str,
        shipping: List[Dict],
        webhook_response_url: Optional[str] = None,
        customer_latitude: float = 0.0,
        customer_longitude: float = 0.0,
    ) -> Dict[str, Any]:
        """
        POST /v1/order/create

        `trans_code` must be a secure code known to the customer (per docs it
        should never be silently auto-generated without the customer's
        awareness) - the caller is responsible for collecting/providing it.

        `shipping` must be the array of per-vendor shipping selections
        returned by `calculate_shipping_fees()` (fee/method_id/config_id/
        company_name), not fabricated locally - Payuee validates these
        server-side against its own shipping configuration.
        """
        full_name = (getattr(order.user, 'full_name', '') or order.user.email or '').strip()
        first_name, _, last_name = full_name.partition(' ')
        first_name = first_name or 'Customer'
        last_name = last_name or '-'

        cart_items_payload = []
        for item in cart_items:
            payuee_product_id = getattr(item.product, 'payuee_product_id', None) or str(item.product.id)
            cart_items_payload.append({
                'product_id': payuee_product_id,
                'cart_meta': {
                    'quantity': item.quantity,
                },
            })

        data = {
            'trans_code': trans_code,
            'webhook_response_url': webhook_response_url or getattr(settings, 'PAYUEE_WEBHOOK_URL', ''),
            'customer': {
                'email': order.user.email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': order.shipping_phone or '',
                'state': order.shipping_state or '',
                'city': order.shipping_city or '',
                'address_1': order.shipping_address or '',
                'address_2': '',
                'order_note': getattr(order, 'customer_note', '') or '',
                'latitude': customer_latitude,
                'longitude': customer_longitude,
            },
            'cart_items': cart_items_payload,
            'shipping': shipping,
        }

        result = self.make_request(
            'POST',
            '/v1/order/create',
            data,
            idempotency_key=order.idempotency_key,
        )

        if result.get('success'):
            payload = result.get('data', {})
            return {
                'success': True,
                'order_ids': payload.get('order_ids', []),
                'status': payload.get('status', 'success'),
                'message': payload.get('message'),
            }

        return {
            'success': False,
            'error': result.get('error', 'Unknown Payuee error'),
            'status_code': result.get('status_code'),
        }

    def get_order(self, payuee_order_id) -> Dict[str, Any]:
        """GET /v1/order/{orderID}"""
        return self.make_request('GET', f'/v1/order/{payuee_order_id}')

    def list_orders(self, page: int = 1, limit: int = 15) -> Dict[str, Any]:
        """GET /v1/order/list"""
        return self.make_request('GET', f'/v1/order/list?page={page}&limit={limit}')

    def scan_qr(self, encrypted: str) -> Dict[str, Any]:
        """POST /v1/order/scan-qr - must be called before verify_delivery()."""
        return self.make_request('POST', '/v1/order/scan-qr', {'encrypted': encrypted})

    def verify_delivery(self, encrypted: str, customer_id, trans_code: str) -> Dict[str, Any]:
        """
        POST /v1/order/verify

        Requires the encrypted QR payload (from scan_qr's flow) plus the
        customer's transaction code - both must be supplied by the caller;
        this client does not fabricate them.
        """
        data = {
            'encrypted': encrypted,
            'customer_id': customer_id,
            'trans_code': trans_code,
        }
        return self.make_request('POST', '/v1/order/verify', data)

    def report_order(self, order_id, report_note: str) -> Dict[str, Any]:
        """POST /v1/order/report"""
        return self.make_request('POST', '/v1/order/report', {
            'order_id': order_id,
            'report_note': report_note,
        })

    def cancel_order(self, order_id, trans_code: str, report_note: str = '') -> Dict[str, Any]:
        """POST /v1/order/cancel"""
        data = {'order_id': order_id, 'trans_code': trans_code}
        if report_note:
            data['report_note'] = report_note
        return self.make_request('POST', '/v1/order/cancel', data)

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------
    def submit_review(self, product_id, user_id, name, email, review, rating) -> Dict[str, Any]:
        """POST /v1/product/review"""
        data = {
            'product_id': product_id,
            'user_id': user_id,
            'name': name,
            'email': email,
            'review': review,
            'rating': rating,
        }
        return self.make_request('POST', '/v1/product/review', data)

    def get_reviews(self, product_id, page: int = 1) -> Dict[str, Any]:
        """GET /v1/product/reviews/{page_number}/{product_id}"""
        return self.make_request('GET', f'/v1/product/reviews/{page}/{product_id}')

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    def test_auth(self) -> Dict[str, Any]:
        """GET /v1/auth-status - quick credential sanity check."""
        return self.make_request('GET', '/v1/auth-status')


# Singleton instance
_payuee_client = None


def get_payuee_client() -> PayueeClient:
    """Get or create the shared Payuee client instance."""
    global _payuee_client
    if _payuee_client is None:
        _payuee_client = PayueeClient()
    return _payuee_client
