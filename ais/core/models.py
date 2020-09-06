from __future__ import annotations
from typing import Tuple, Dict, Any, List
from typing import TYPE_CHECKING
import io
import csv

import json
import msgpack

from django.contrib.gis.db import models
from django.db import connections
from django.db.models.base import ModelBase
from django.contrib.gis.geos import Polygon

from core.serializers import msgpack as ms
from core.serializers import json as js
from core.serializers import csv as cs
from core import shiptype

from ais.settings import DIALECT_NAME

import logging
from logformat import StyleAdapter

if TYPE_CHECKING:
    from django.db.models.query import RawQuerySet, QuerySet


logger = StyleAdapter(logging.getLogger(__name__))

"""The raw ais data in a dictionary form"""
AisData = Dict[str, Any]


class ShipTypeManager(models.Manager):
    def prepopulate(self) -> None:
        st_list = [self.model(
            st.type,
            st.short_name,
            st.name,
            st.summary,
            st.details
        ) for st in shiptype.shiptype_generator()]

        self.bulk_create(st_list)


class ShipType(models.Model):
    type_id = models.IntegerField(primary_key=True)
    short_name = models.CharField(max_length=128, null=False, blank=False)
    name = models.CharField(max_length=128, null=False, blank=False)
    summary = models.CharField(max_length=128, null=False, blank=False)
    details = models.CharField(
        max_length=512, null=True, blank=True, default='')

    objects = ShipTypeManager()


class AisMeta:
    """Some useful fields used by AdditionalMeta"""

    def __init__(self, class_):
        self.required_fields = [f.name for f in class_._meta.fields
                                if not f.blank]
        self.not_null_str_fields = {f.name for f in class_._meta.fields
                                    if f.blank and not f.null} - {'id'}
        self.fields_name = set(f.name for f in class_._meta.fields) - {'id'}
        self.sorted_fields_name = sorted(self.fields_name)


class AdditionalMeta(ModelBase):
    """Metaclass used to add some useful fields to BaseInfos in a _aismeta
    fields"""
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
    valid_position = models.BooleanField(
        null=True, blank=True, default=False)
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

    def __repr__(self) -> str:
        return '{0}: ({1}, {2})'.format(
            type(self).__name__,
            self.mmsi,
            str(self.time)
        )


class ShipInfos(BaseInfos):
    """Concrete class for the table holding the ship informations sent by AIS"""
    # TODO: normalize other fields
    mmsi = models.IntegerField(primary_key=True)

    DEFAULT_LENGTH = 10
    DEFAULT_WIDTH = 3
    DEFAULT_WKT = 'POLYGON((-0.5 -1, 0 1, 0.5 -1, 0 -0.75, -0.5 -1))'

    def normalize_dims(self) -> Tuple(float, float, float, float):
        """Return the dimensions of the boat with default value when missing
        The order is (bow, stern, port, starboard)"""
        bow, stern = [
            0 if e == 511 else e for e in (self.dim_bow, self.dim_stern)
        ]
        if bow+stern == 0:
            bow = stern = self.DEFAULT_LENGTH / 2

        port, starboard = [
            0 if e == 63 else e for e in (self.dim_port, self.dim_starboard)
        ]
        if port+starboard == 0:
            port = starboard = self.DEFAULT_WIDTH / 2

        return (bow, stern, port, starboard)

    @property
    def ship_wkt(self) -> str:
        """Compute the ship shape as a wkt string"""
        bow, stern, port, starboard = self.normalize_dims()

        middle = round((starboard-port)/2, 3)
        before_bow = round(bow - (0.2*(bow+stern)), 3)
        wkt = (
            f"POLYGON((-{port} -{stern}, -{port} {before_bow}, "
            f"{middle} {bow}, {starboard} {before_bow}, "
            f"{starboard} -{stern}, -{port} -{stern}))"
        )
        return wkt

    @property
    def length(self) -> int:
        """Return the length of the ship"""
        bow, stern, _, _ = self.normalize_dims()
        return bow+stern

    @property
    def width(self) -> int:
        """Return the width of the ship"""
        _, _, port, starboard = self.normalize_dims()
        return port+starboard


class MessageQuerySet(models.QuerySet):
    def history(self, mmsi: int, max_message: int = None) -> QuerySet:
        """Get the messages of a particular mmsi in time desc order"""
        if max_message is not None:
            return (self.filter(mmsi=mmsi).
                    order_by('-mmsi', '-time')[:max_message])
        return (self.filter(mmsi=mmsi).  order_by('-mmsi', '-time'))


class Message(BaseInfos):
    """Concrete class for the table holding the messages sent by AIS"""
    mmsi = models.ForeignKey(ShipInfos, on_delete=models.DO_NOTHING,
                             db_column='mmsi')
    objects = MessageQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('mmsi', 'time',),
                name='core_message_uniq_mmsi_time'
            )
        ]


def copy_csv(f: io.TextIOBase, sep: str = '|', null: str = '',
             escape='\\', quote='\"', keep_history=True) -> Tuple[int, int]:
    """Copy Message in f in a csv format to a temporary table then update
    core_message and core_shipinfos tables"""

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

        logger.debug('temporary table created')

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

        logger.debug('COPY ended')

        # upsert into core_lastmessage table
        table_name = ShipInfos._meta.db_table
        fields_name = ShipInfos._aismeta.sorted_fields_name
        fields_name_str = ','.join(fields_name)
        excluded_fields_name = ','.join(
            'excluded.{}'.format(f) for f in fields_name)
        # TODO: use recursive instead of distinct... maybe
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

        logger.debug('UPSERT ended')

        new_messages = 0
        if keep_history:
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

            logger.debug('INSERT ended')

        # cleanup
        drop_tmp_table = 'DROP TABLE {0}'.format(tmp_table_name)
        cursor.execute(drop_tmp_table)

        return (new_messages, new_shipinfos,)
    # TODO: Bad execution here... do something ?
    logger.error('temporary error here')


def _copy_data(data: List[AisData],
               sep: str = '|', null: str = '') -> Tuple[int, int]:
    """Copy AisData list to the database using copy_csv
    Convenience method for test, should not be used outside as it uses List and
    might be memory heavy"""
    csv_data = [{k: cs.default_encoder(v) for k, v in d.items()}
                for d in data]

    f = io.StringIO()
    writer = csv.DictWriter(f, BaseInfos._aismeta.sorted_fields_name,
                            dialect=DIALECT_NAME)
    writer.writerows(csv_data)
    f.seek(0)
    return copy_csv(f, sep, null)
