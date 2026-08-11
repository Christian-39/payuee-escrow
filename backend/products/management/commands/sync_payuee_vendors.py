"""
Sync payuee_vendor_id for all Payuee products.
"""
from django.core.management.base import BaseCommand
from products.models import Product
from payments.payuee_client import PayueeClient
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync eshop_user_id (vendor ID) for all Payuee products from Payuee API'

    def handle(self, *args, **options):
        client = PayueeClient()
        
        # Get all Payuee products without vendor ID
        products = Product.objects.filter(source='payuee')
        total = products.count()
        
        self.stdout.write(f"Found {total} Payuee products to sync")
        
        updated = 0
        failed = 0
        
        for product in products:
            if not product.payuee_product_id:
                self.stdout.write(
                    self.style.WARNING(f"Skipping {product.name}: no payuee_product_id")
                )
                failed += 1
                continue
            
            try:
                # Fetch product details from Payuee
                result = client.get_product(int(product.payuee_product_id))
                
                if not result.get('success'):
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to fetch {product.name} (ID: {product.payuee_product_id}): "
                            f"{result.get('error', 'Unknown error')}"
                        )
                    )
                    failed += 1
                    continue
                
                data = result.get('data', {}).get('success', {})
                eshop_user_id = data.get('eshop_user_id')
                
                if eshop_user_id:
                    product.payuee_vendor_id = str(eshop_user_id)
                    product.save(update_fields=['payuee_vendor_id'])
                    updated += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated {product.name}: vendor_id={eshop_user_id}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No vendor ID found for {product.name}"
                        )
                    )
                    failed += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing {product.name}: {str(e)}")
                )
                failed += 1
        
        self.stdout.write("=" * 50)
        self.stdout.write(f"Total products: {total}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Failed: {failed}")