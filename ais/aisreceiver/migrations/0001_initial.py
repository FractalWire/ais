# Generated by Django 2.2.4 on 2019-08-22 15:35

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
                ('mmsi', models.CharField(max_length=16)),
                ('time', models.DateTimeField()),
                ('longitude', models.FloatField()),
                ('latitude', models.FloatField()),
                ('cog', models.FloatField(default=360.0)),
                ('sog', models.FloatField(default=102.4)),
                ('heading', models.IntegerField(default=511)),
                ('pac', models.BooleanField(default=0)),
                ('rot', models.IntegerField(default=0)),
                ('navstat', models.IntegerField(default=15)),
                ('imo', models.CharField(max_length=16)),
                ('callsign', models.CharField(max_length=16)),
                ('name', models.CharField(max_length=128)),
                ('ship_type', models.IntegerField(default=0)),
                ('dim_bow', models.IntegerField(default=0)),
                ('dim_stern', models.IntegerField(default=0)),
                ('dim_port', models.IntegerField(default=0)),
                ('dim_starboard', models.IntegerField(default=0)),
                ('eta', models.DateTimeField(default=None, null=True)),
                ('draught', models.FloatField(default=0.0)),
                ('destination', models.CharField(blank=True, default='', max_length=256)),
            ],
            options={
                'unique_together': {('mmsi', 'time')},
            },
        ),
    ]