# Generated by Django 4.0.4 on 2023-06-26 18:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('faucet', '0048_globalsettings_prizetap_weekly_claim_limit_and_more'),
        ('prizetap', '0003_raffle_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='raffle',
            name='contract',
            field=models.CharField(default=0, max_length=256),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='raffle',
            name='raffleId',
            field=models.BigIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='raffle',
            name='signer',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, to='faucet.walletaccount'),
            preserve_default=False,
        ),
    ]
