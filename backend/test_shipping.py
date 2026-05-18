# test_shipping.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gadgethub.settings')
django.setup()

import json
from payments.payuee_client import PayueeClient

client = PayueeClient()

# Test with exact Payuee docs example
test_payload = {
    "vendors": [5, 9],
    "state": "Lagos",
    "city": "Lekki",
    "latitude": 6.4474,
    "longitude": 3.3903,
    "cart_items": [
        {
            "product_id": 12,
            "eshop_user_id": 5,
            "quantity": 2
        }
    ]
}

print("=" * 60)
print("TESTING PAYUEE SHIPPING WITH DOCS EXAMPLE")
print("=" * 60)
result = client.get_shipping_fees(**test_payload)
print(json.dumps(result, indent=2, default=str))