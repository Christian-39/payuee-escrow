"""
Data migration: null out any plaintext Payuee transaction PINs left over
on Order.trans_code from before that field was made write-disabled (see
orders/models.py and orders/views.py - checkout() no longer persists the
raw PIN there; it's verified against User.payuee_transaction_pin_hash and
used in-memory only for the Payuee API call).

This does NOT touch User.payuee_transaction_pin_hash, which was already
correctly hashed and is unaffected. It only clears the field on Order rows
- existing orders remain otherwise intact; there is no need to
re-authorize or re-verify them with Payuee, since Payuee's own record of
the order/escrow is unaffected by this local field being cleared.

Safe to run multiple times (idempotent) and reversible as a no-op (the
plaintext values are gone for good once cleared - by design, since the
whole point is that they should never have been stored).
"""

from django.db import migrations


def clear_plaintext_trans_codes(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    Order.objects.exclude(trans_code__isnull=True).exclude(trans_code='').update(trans_code=None)


def noop_reverse(apps, schema_editor):
    # Intentional no-op: the cleared plaintext PINs cannot and should not
    # be restored (see module docstring). Reversing this migration simply
    # leaves the field cleared.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_order_shipping_latitude_and_more'),
    ]

    operations = [
        migrations.RunPython(clear_plaintext_trans_codes, noop_reverse),
    ]
