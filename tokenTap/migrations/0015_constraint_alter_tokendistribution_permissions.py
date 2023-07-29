# Generated by Django 4.0.4 on 2023-07-20 10:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tokenTap', '0014_alter_tokendistributionclaim_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Constraint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('BrightIDMeetVerification', 'BrightIDMeetVerification'), ('BrightIDAuraVerification', 'BrightIDAuraVerification')], max_length=255, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('type', models.CharField(choices=[('VER', 'Verification'), ('TIME', 'Time')], default='VER', max_length=10)),
                ('description', models.TextField(blank=True, null=True)),
                ('response', models.TextField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='tokendistribution',
            name='permissions',
            field=models.ManyToManyField(blank=True, to='tokenTap.constraint'),
        ),
    ]
