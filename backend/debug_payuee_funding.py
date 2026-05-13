#!/usr/bin/env python3
"""
Debug script to test Payuee wallet funding details API directly.
Run with: python debug_payuee_funding.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gadgethub.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import json
import logging
from payments.payuee_client import PayueeClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_funding_details():
    client = PayueeClient()
    result = client.get_wallet_funding_details()

    print("=" * 60)
    print("PAYUEE WALLET FUNDING DETAILS - RAW RESPONSE")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))
    print("=" * 60)

    if result.get('success'):
        data = result.get('data', {})
        print(f"\nAvailable keys in data: {list(data.keys())}")

        possible_keys = [
            'wallet_funding_account',
            'fund',
            'wallet_funding_details',
            'funding_account',
            'account',
            'wallet_funding',
            'virtual_account',
            'bank_details',
        ]

        print("\nChecking for funding account data:")
        for key in possible_keys:
            value = data.get(key)
            if value:
                print(f"  ✓ Found '{key}': {json.dumps(value, indent=4, default=str)}")
            else:
                print(f"  ✗ '{key}': not found")
    else:
        print(f"\nRequest failed: {result.get('error')}")
        print(f"Status code: {result.get('status_code')}")


if __name__ == '__main__':
    test_funding_details()