from __future__ import annotations
from django.contrib.gis.db import models

from typing import NamedTuple
from datetime import datetime


class Message(models.Model):
    """Various informations sent by the vessel via AIS"""
    mmsi = models.CharField(max_length=16)
    time = models.DateTimeField()
    # longitude = models.FloatField()
    # latitude = models.FloatField()
    point = models.PointField(geography=True)
    valid_position = models.BooleanField(default=True)
    cog = models.FloatField(default=360.0)
    sog = models.FloatField(default=102.4)
    heading = models.IntegerField(default=511)
    pac = models.BooleanField(default=0)
    rot = models.IntegerField(default=0)
    navstat = models.IntegerField(default=15)

    imo = models.CharField(max_length=16, blank=True, default='')
    callsign = models.CharField(max_length=16, blank=True, default='')
    name = models.CharField(max_length=128, blank=True, default='')
    ship_type = models.IntegerField(default=0)
    dim_bow = models.IntegerField(default=0)
    dim_stern = models.IntegerField(default=0)
    dim_port = models.IntegerField(default=0)
    dim_starboard = models.IntegerField(default=0)
    eta = models.DateTimeField(null=True, blank=True, default=None)
    draught = models.FloatField(default=0.)
    destination = models.CharField(max_length=256, blank=True, default='')

    class Meta:
        unique_together = ('mmsi', 'time',)

    def __repr__(self) -> str:
        return 'Message({0}): ({1}, {2}, {3})'.format(
            self.id,
            self.mmsi,
            str(self.time),
            str(self.point)
        )
