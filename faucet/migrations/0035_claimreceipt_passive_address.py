# Generated by Django 4.0.4 on 2023-03-23 10:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faucet', '0034_alter_claimreceipt_user_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='claimreceipt',
            name='passive_address',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]
