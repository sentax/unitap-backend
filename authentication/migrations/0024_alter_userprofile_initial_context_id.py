# Generated by Django 4.0.4 on 2023-12-20 19:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0023_wallet_created_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='initial_context_id',
            field=models.CharField(blank=True, max_length=512, null=True, unique=True),
        ),
    ]
