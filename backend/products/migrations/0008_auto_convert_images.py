from django.db import migrations


def convert_images_to_json(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    
    for product in Product.objects.all():
        old = product.images
        
        if old is None or old == '' or old == 'null':
            product.images = '[]'  # JSON string for empty array
        elif isinstance(old, str) and not old.startswith('['):
            # Single image path -> JSON array string
            import json
            product.images = json.dumps([old])
        # If already starts with [, assume it's already JSON
        
        # Use raw SQL to bypass Django validation
        schema_editor.execute(
            "UPDATE products SET images = %s WHERE id = %s",
            [product.images, str(product.id)]
        )


class Migration(migrations.Migration):
    # REPLACE THIS with your actual last migration
    atomic = False
    dependencies = [
        ('products', '0007_remove_product_products_is_feat_19b203_idx_and_more'),  # <-- USE YOUR REAL LAST MIGRATION
    ]

    operations = [
        migrations.RunPython(convert_images_to_json),
    ]