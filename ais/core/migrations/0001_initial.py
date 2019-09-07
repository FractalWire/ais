# Generated by Django 2.2.4 on 2019-09-05 14:27

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mmsi', models.IntegerField()),
                ('time', models.DateTimeField()),
                ('point', django.contrib.gis.db.models.fields.PointField(blank=True, default=None, geography=True, null=True, srid=4326)),
                ('valid_position', models.BooleanField(blank=True, default=False, null=True)),
                ('cog', models.FloatField(blank=True, default=None, null=True)),
                ('sog', models.FloatField(blank=True, default=None, null=True)),
                ('heading', models.IntegerField(blank=True, default=None, null=True)),
                ('pac', models.BooleanField(blank=True, default=None, null=True)),
                ('rot', models.IntegerField(blank=True, default=None, null=True)),
                ('navstat', models.IntegerField(blank=True, default=None, null=True)),
                ('imo', models.IntegerField(blank=True, default=None, null=True)),
                ('callsign', models.CharField(blank=True, default='', max_length=16)),
                ('name', models.CharField(blank=True, default='', max_length=128)),
                ('ship_type', models.IntegerField(blank=True, default=None, null=True)),
                ('dim_bow', models.IntegerField(blank=True, default=None, null=True)),
                ('dim_stern', models.IntegerField(blank=True, default=None, null=True)),
                ('dim_port', models.IntegerField(blank=True, default=None, null=True)),
                ('dim_starboard', models.IntegerField(blank=True, default=None, null=True)),
                ('eta', models.DateTimeField(blank=True, default=None, null=True)),
                ('draught', models.FloatField(blank=True, default=None, null=True)),
                ('destination', models.CharField(blank=True, default='', max_length=256)),
            ],
        ),
        migrations.AddConstraint(
            model_name='message',
            constraint=models.UniqueConstraint(fields=('mmsi', 'time'), name='core_message_uniq_mmsi_timedesc'),
        ),
    ]
