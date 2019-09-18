from __future__ import annotations
from typing import Tuple, Dict, Any, List
from logformat import StyleAdapter
import logging
from typing import TYPE_CHECKING
import io
import csv

import json
import msgpack

from django.contrib.gis.db import models
from django.db import connections
from django.db.models.base import ModelBase

from core.serializers import msgpack as ms
from core.serializers import json as js
from core.serializers import csv as cs

if TYPE_CHECKING:
    from io import TextIOBase


logger = StyleAdapter(logging.getLogger(__name__))

"""The raw ais data in a dictionary form"""
AisData = Dict[str, Any]


class AisMeta:
    def __init__(self, class_):
        self.required_fields = [f.name for f in class_._meta.fields
                                if not f.blank]
        self.not_null_str_fields = {f.name for f in class_._meta.fields
                                    if f.blank and not f.null} - {'id'}
        self.fields_name = set(f.name for f in class_._meta.fields) - {'id'}
        self.sorted_fields_name = sorted(self.fields_name)


class AdditionalMeta(ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        class_ = super().__new__(cls, name, bases, attrs, **kwargs)
        aismeta = AisMeta(class_)
        class_._aismeta = aismeta

        return class_


class BaseInfos(models.Model, metaclass=AdditionalMeta):
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
    def from_msgpack(cls, msgpack_object: bytes) -> Message:
        """Factory to build a BaseMessage from a msgpack object"""
        msg_dict = msgpack.unpackb(msgpack_object,
                                   object_hook=ms.object_decoder,
                                   raw=False)
        return cls(**msg_dict)

    @classmethod
    def from_json(cls, json_object: str) -> Message:
        """Factory to build a BaseMessage from a json object"""
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
        return 'Message: ({0}, {1})'.format(
            self.mmsi,
            str(self.time)
        )


class ShipInfos(BaseInfos):
    """Concrete class for the table holding the ship informations sent by AIS"""
    mmsi = models.IntegerField(primary_key=True)


class Message(BaseInfos):
    """Concrete class for the table holding the messages sent by AIS"""
    mmsi = models.ForeignKey(ShipInfos, on_delete=models.DO_NOTHING,
                             db_column='mmsi')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('mmsi', 'time',),
                name='core_message_uniq_mmsi_time'
            )
        ]


def copy_csv(f: TextIOBase, sep: str = '|', null: str = '',
             escape='\\', quote='\"') -> Tuple[int, int]:
    """Copy Message in f in a csv format to a temporary table then update
    core_message and core_lastmessage tables"""
    with connections['default'].cursor() as cursor:
        # Create temp table
        table_name = Message._meta.db_table
        tmp_table_name = 'tmp_{0}'.format(Message._meta.db_table)
        fields_name = Message._aismeta.sorted_fields_name
        fields_name_str = ','.join(fields_name)
        create_tmp_table_query = (
            'CREATE TEMPORARY TABLE {0} AS'
            ' SELECT {1} FROM {2} limit 0'.format(
                tmp_table_name,
                fields_name_str,
                table_name
            )
        )
        cursor.execute(create_tmp_table_query)

        # TODO: need quote and escape testing
        copy_query = (
            'COPY {0} FROM STDIN WITH'
            ' (FORMAT csv, DELIMITER \'{1}\', NULL \'{2}\''
            ', ESCAPE \'{3}\', QUOTE \'"\')'
            .format(
                tmp_table_name,
                sep,
                null,
                escape
            )
        )
        cursor.copy_expert(copy_query, f)

        # upsert into core_lastmessage table
        table_name = ShipInfos._meta.db_table
        fields_name = ShipInfos._aismeta.sorted_fields_name
        fields_name_str = ','.join(fields_name)
        excluded_fields_name = ','.join(
            'excluded.{}'.format(f) for f in fields_name)
        upsert_query = (
            'INSERT INTO {0} AS lm ({1})'
            ' SELECT DISTINCT ON (mmsi) {1} FROM {2} ORDER BY mmsi, time DESC'
            ' ON CONFLICT (mmsi) DO UPDATE'
            ' SET ({1}) = ({3})'
            ' WHERE lm.time < excluded.time'.format(
                table_name,
                fields_name_str,
                tmp_table_name,
                excluded_fields_name
            )
        )
        cursor.execute(upsert_query)
        new_shipinfos = cursor.rowcount

        # Insert into core_message table
        table_name = Message._meta.db_table
        fields_name = Message._aismeta.sorted_fields_name
        fields_name_str = ','.join(fields_name)
        insert_query = (
            'INSERT INTO {0} ({1})'
            ' SELECT {1} FROM {2}'
            ' ON CONFLICT DO NOTHING'.format(
                table_name,
                fields_name_str,
                tmp_table_name
            )
        )
        cursor.execute(insert_query)
        new_messages = cursor.rowcount

        # cleanup
        drop_tmp_table = 'DROP TABLE {0}'.format(tmp_table_name)
        cursor.execute(drop_tmp_table)

        return (new_messages, new_shipinfos,)
    # TODO: Bad execution here... do something ?
    logger.error('temporary error here')


def copy_data(data: List[AisData],
              sep: str = '|', null: str = '') -> Tuple[int, int]:
    """Copy AisData list to the database using copy_csv
    Convenience method for test, should not be used outside as it uses List and
    might be memory heavy"""
    csv_data = [{k: cs.default_encoder(v) for k, v in d.items()}
                for d in data]

    csv.register_dialect('postgres', delimiter='|', escapechar='\\',
                         lineterminator='\n', quoting=csv.QUOTE_NONE,
                         quotechar='', strict=True)
    f = io.StringIO()
    writer = csv.DictWriter(f, BaseInfos._aismeta.sorted_fields_name,
                            dialect='postgres')
    writer.writerows(csv_data)
    f.seek(0)
    return copy_csv(f, sep, null)
