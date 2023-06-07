# Generated by Django 4.0.4 on 2023-06-07 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tokenTap', '0010_rename_distributer_tokendistribution_distributor_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokendistribution',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='tokendistribution',
            name='distributor',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
