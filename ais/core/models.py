from __future__ import annotations
from typing import List, Set, Tuple
from logformat import StyleAdapter
import logging
from typing import TYPE_CHECKING

import json
import msgpack

from django.contrib.gis.db import models
from django.db import connections

from core.serializers import msgpack as ms
from core.serializers import json as js

if TYPE_CHECKING:
    from io import TextIOBase


logger = StyleAdapter(logging.getLogger(__name__))


class BaseMessage(models.Model):
    """Abstract base class for various informations sent by the vessel via AIS"""
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
        abstract = True

    @classmethod
    def required_fields(cls) -> List[str]:
        return [f.name for f in cls._meta.get_fields()
                if not f.blank]

    @classmethod
    def not_null_str_fields(cls) -> Set[str]:
        return {f.name for f in cls._meta.get_fields()
                if f.blank and not f.null} - {'id'}

    @classmethod
    def fields_name(cls) -> Set[str]:
        return set(f.name for f in cls._meta.fields)

    @classmethod
    def sorted_fields_name(cls) -> List[str]:
        return sorted(cls.fields_name())

    # @staticmethod
    # def not_available_value() -> Dict[str, Any]:
    #     return dict(
    #         point=None,
    #         valid_position=False,
    #         cog=360.0,
    #         sog=102.4,
    #         heading=511,
    #         navstat=15,
    #         ship_type=0,
    #         dim_bow=0,
    #         dim_stern=0,
    #         dim_port=0,
    #         dim_starboard=0,
    #     )

    # @staticmethod
    # def infos_keys() -> Set[str]:
    #     return {
    #         'mmsi',
    #         'imo',
    #         'callsign',
    #         'name',
    #         'ship_type',
    #         'dim_bow',
    #         'dim_stern',
    #         'dim_port',
    #         'dim_starboard',
    #         'eta',
    #         'draught',
    #         'destination',
    #     }

    # @staticmethod
    # def position_keys() -> Set[str]:
    #     return {
    #         'mmsi',
    #         'time',
    #         'point',
    #         'valid_position',
    #         'cog',
    #         'sog',
    #         'heading',
    #         'pac',
    #         'rot',
    #         'navstat',
    #     }

    @classmethod
    def from_msgpack(cls, msgpack_object: bytes) -> Message:
        """Factory to build a Message from a msgpack object"""
        msg_dict = msgpack.unpackb(msgpack_object,
                                   object_hook=ms.object_decoder,
                                   raw=False)
        return cls(**msg_dict)

    @classmethod
    def from_json(cls, json_object: str) -> Message:
        """Factory to build a Message from a json object"""
        msg_dict = json.loads(json_object,
                              object_hook=js.object_decoder)
        return cls(**msg_dict)

    # @classmethod
    # def random(cls) -> Message:
    #     """Quick and dirty random factory
    #     !!! TODO: Not for production !!! """
    #     import random
    #     from datetime import datetime
    #     from django.contrib.gis.geos import Point
    #     return cls(
    #         mmsi=random.randrange(10**6, 10**7),
    #         time=datetime.now(),
    #         point=Point(random.randrange(0, 100), random.randrange(0, 90)),
    #         valid_position=True,
    #         cog=random.random()*360,
    #         sog=random.random()*360,
    #         heading=int(random.random()*360),
    #         pac=False,
    #         rot=int(random.random()*360),
    #         navstat=int(random.random()*360),
    #         imo=int(random.random()*360),
    #         callsign='',
    #         name='',
    #         ship_type=int(random.random()*360),
    #         dim_bow=int(random.random()*360),
    #         dim_stern=int(random.random()*360),
    #         dim_port=int(random.random()*360),
    #         dim_starboard=int(random.random()*360),
    #         eta=None,
    #         draught=random.random()*360,
    #         destination=''
    #     )

    def __repr__(self) -> str:
        return 'Message({0}): ({1}, {2}, {3})'.format(
            self.id,
            self.mmsi,
            str(self.time),
            str(self.point)
        )


class Message(BaseMessage):
    """Concrete class for the table holding the messages sent by AIS"""
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('mmsi', 'time',),
                name='core_message_uniq_mmsi_time'
            )
        ]

    @classmethod
    def fields_name(cls):
        return super().fields_name() - {'id'}


class LastMessage(BaseMessage):
    """Concrete class for the table holding the last messages sent by AIS"""
    mmsi = models.IntegerField(primary_key=True)
