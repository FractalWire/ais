from __future__ import annotations
from django.contrib.gis.db import models


class Message(models.Model):
    """Various informations sent by the vessel via AIS"""
    mmsi = models.IntegerField()
    time = models.DateTimeField()
    point = models.PointField(null=True, blank=True,
                              geography=True, default=None)
    valid_position = models.BooleanField(null=True, blank=True, default=False)
    cog = models.FloatField(null=True, blank=True, default=None)
    sog = models.FloatField(null=True, blank=True, default=None)
    heading = models.IntegerField(null=True, blank=True, default=None)
    pac = models.BooleanField(null=True, blank=True, default=None)
    rot = models.IntegerField(null=True, blank=True, default=None)
    navstat = models.IntegerField(null=True, blank=True, default=None)

    imo = models.IntegerField(null=True, blank=True, default=None)
    callsign = models.CharField(max_length=16, blank=True, default='')
    name = models.CharField(max_length=128, blank=True, default='')
    ship_type = models.IntegerField(null=True, blank=True, default=None)
    dim_bow = models.IntegerField(null=True, blank=True, default=None)
    dim_stern = models.IntegerField(null=True, blank=True, default=None)
    dim_port = models.IntegerField(null=True, blank=True, default=None)
    dim_starboard = models.IntegerField(null=True, blank=True, default=None)
    eta = models.DateTimeField(null=True, blank=True, default=None)
    draught = models.FloatField(null=True, blank=True, default=None)
    destination = models.CharField(max_length=256, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('mmsi', 'time',),
                name='core_message_uniq_mmsi_time'
            )
        ]

    @staticmethod
    def not_available_value():
        return dict(
            point=None,
            valid_position=False,
            cog=360.0,
            sog=102.4,
            heading=511,
            navstat=15,
            ship_type=0,
            dim_bow=0,
            dim_stern=0,
            dim_port=0,
            dim_starboard=0,
        )

    @staticmethod
    def infos_keys():
        return {
            'mmsi',
            'imo',
            'callsign',
            'name',
            'ship_type',
            'dim_bow',
            'dim_stern',
            'dim_port',
            'dim_starboard',
            'eta',
            'draught',
            'destination',
        }

    @staticmethod
    def position_keys():
        return {
            'mmsi',
            'time',
            'point',
            'valid_position',
            'cog',
            'sog',
            'heading',
            'pac',
            'rot',
            'navstat',
        }

    @classmethod
    def required_fields(cls):
        return [f.name for f in cls._meta.get_fields()
                if not getattr(f, 'blank', False)]

    def __repr__(self) -> str:
        return 'Message({0}): ({1}, {2}, {3})'.format(
            self.id,
            self.mmsi,
            str(self.time),
            str(self.point)
        )
