# Generated by Django 4.0.4 on 2023-06-30 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('prizetap', '0006_remove_raffle_winner_raffleentry_is_winner'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='raffleentry',
            name='nonce',
        ),
    ]
