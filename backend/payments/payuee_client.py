# ============================================================
# FILE 3: payments/payuee_client.py (UPDATED PRODUCTION READY)
# ============================================================
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
        self.api_key = settings.PAYUEE_API_KEY          # Public Key (payuee_pk_live_...)
        self.api_secret = settings.PAYUEE_API_SECRET    # Secret Key (payuee_sk_live_...)
        self.base_url = getattr(settings, 'PAYUEE_BASE_URL', 'https://escrow.payuee.com/v1')
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
        """
        Generate HMAC SHA256 signature for outbound API requests.
        Format: payload = timestamp + UPPERCASE(HTTP_METHOD) + request_path + request_body
        """
        if timestamp is None:
            timestamp = str(int(time.time()))

        # Enforce exact format specified by Payuee API reference docs
        payload = f"{timestamp}{method.upper()}{path}{body}"

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return timestamp, signature

    def make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send authenticated request to Payuee Core Engine."""
        url = f"{self.base_url}{path}"
        body_str = json.dumps(data) if data else ''
        
        timestamp, signature = self.generate_signature(method, path, body_str)
        
        headers = {
            "Authorization": f"Bearer {self.api_secret}",
            "X-Payuee-Public-Key": self.api_key,
            "X-Payuee-Timestamp": timestamp,
            "X-Payuee-Signature": signature,
            "X-Payuee-Idempotency-Key": idempotency_key or f"req_{int(time.time() * 1000)}",
            "Content-Type": "application/json"
        }

        try:
            logger.info(f"Making {method} request to Payuee: {url}")
            if data:
                response = requests.request(method, url, headers=headers, data=body_str, timeout=30)
            else:
                response = requests.request(method, url, headers=headers, timeout=30)
                
            # Handle standard error cases mapped to status codes cleanly
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Payuee API Error [{response.status_code}]: {response.text}")
                return {
                    "success": False,
                    "error_code": f"HTTP_{response.status_code}",
                    "message": response.text
                }
        except Exception as e:
            logger.exception(f"Connection failure to Payuee endpoint {path}")
            return {
                "success": False,
                "error_code": "CONNECTION_FAILURE",
                "message": str(e)
            }

    # ─────────────────────────────────────────────────────────────
    # PRODUCTS PASSTHROUGH ENPOINTS
    # ─────────────────────────────────────────────────────────────

    def list_products(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch store inventory filtered by category, location coordinates, or pricing."""
        return self.make_request('POST', '/products', data)

    def search_products(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced query searching across products with multi-tag array filtering."""
        return self.make_request('POST', '/products/search', data)

    def get_product_details(self, product_id: int) -> Dict[str, Any]:
        """Retrieve single product specs and relation matrix map."""
        return self.make_request('GET', f'/product/{product_id}')

    # ─────────────────────────────────────────────────────────────
    # WALLET ENDPOINTS
    # ─────────────────────────────────────────────────────────────

    def get_wallet_balance(self) -> Dict[str, Any]:
        """Check the primary prefunded corporate operational balance availability."""
        return self.make_request('GET', '/wallet/balance')

    def get_wallet_funding_details(self) -> Dict[str, Any]:
        """Fetch dedicated static dynamic virtual business account data allocations."""
        return self.make_request('GET', '/wallet/fund')

    # ─────────────────────────────────────────────────────────────
    # GEOGRAPHIC / LOGISTICS SERVICE ENDPOINTS
    # ─────────────────────────────────────────────────────────────

    def get_supported_states(self) -> Dict[str, Any]:
        """List active delivery geopolitical boundaries and states."""
        return self.make_request('GET', '/location/states')

    def get_supported_cities(self, state_name: str) -> Dict[str, Any]:
        """Fetch regional LGAs/Wards display matrix blocks matching state string."""
        return self.make_request('GET', f'/location/cities?state={state_name}')

    def calculate_shipping_fees(self, infrastructure_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate multicarrier routing fees per item/vendor grouping array."""
        return self.make_request('POST', '/order/shipping-fees', infrastructure_payload)

    # ─────────────────────────────────────────────────────────────
    # ESCROW & LIFECYCLE MANAGEMENT ENDPOINTS
    # ─────────────────────────────────────────────────────────────

    def create_escrow_order(self, deployment_payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        """Instantiate tracking order pipeline, automatically locking funds in escrow."""
        return self.make_request('POST', '/order/create', deployment_payload, idempotency_key=idempotency_key)

    def get_order_by_id(self, order_id: int) -> Dict[str, Any]:
        """Retrieve historical state status details regarding locked escrow targets."""
        return self.make_request('GET', f'/order/{order_id}')

    def list_historical_orders(self, page: int = 1, limit: int = 15) -> Dict[str, Any]:
        """Fetch systematic audit lists detailing platform integrated pipeline steps."""
        return self.make_request('GET', f'/order/list?page={page}&limit={limit}')

    def scan_qr(self, encrypted_payload: str) -> Dict[str, Any]:
        """Validate courier proximity match via physical package hardware code scanner scanning."""
        return self.make_request('POST', '/v1/order/scan-qr', {"encrypted": encrypted_payload})

    def verify_order(self, encrypted: str, customer_id: int, trans_code: str) -> Dict[str, Any]:
        """Execute cryptographic 2FA authorization verification releasing funds out of escrow."""
        return self.make_request('POST', '/order/verify', {
            "encrypted": encrypted,
            "customer_id": customer_id,
            "trans_code": trans_code,
        })

    def report_order(self, order_id: int, report_note: str) -> Dict[str, Any]:
        """Flag transaction dispute layers, holding funds within internal review vaults."""
        return self.make_request('POST', '/order/report', {
            "order_id": order_id,
            "report_note": report_note,
        })

    def cancel_order(self, order_id: int, trans_code: str, report_note: str = '') -> Dict[str, Any]:
        """Reverse atomic escrow allocation within the authorized 30% delivery duration window."""
        data = {
            "order_id": order_id,
            "trans_code": trans_code,
        }
        if report_note:
            data['report_note'] = report_note
        return self.make_request('POST', '/order/cancel', data)


# Singleton instance tracker
_payuee_client = None

def get_payuee_client() -> PayueeClient:
    global _payuee_client
    if _payuee_client is None:
        _payuee_client = PayueeClient()
    return _payuee_client
