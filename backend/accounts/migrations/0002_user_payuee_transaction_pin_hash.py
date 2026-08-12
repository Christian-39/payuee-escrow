from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='payuee_transaction_pin_hash',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
