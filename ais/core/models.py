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
from django.contrib.gis.geos import Polygon

from core.serializers import msgpack as ms
from core.serializers import json as js
from core.serializers import csv as cs

from ais.settings import DIALECT_NAME

if TYPE_CHECKING:
    from django.db.models.query import RawQuerySet, QuerySet


logger = StyleAdapter(logging.getLogger(__name__))

"""The raw ais data in a dictionary form"""
AisData = Dict[str, Any]


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


class BaseInfosQuerySet(models.QuerySet):
    def bounding_box(self, xmin: float, ymin: float,
                     xmax: float, ymax: float, limit: int = None) -> RawQuerySet:
        """Filter Ship Infos in a particular bounding_box
        !!! Must be used on a small dataset !!!
        TODO: this won't work well above the pole... 80 to 95 is impossible for
        example
        TODO: test
        """
        def create_poly(xmin: float, ymin: float,
                        xmax: float, ymax: float) -> Polygon:
            bbox = (xmin, ymin, xmax, ymax)
            geom = Polygon.from_bbox(bbox)
            # TODO: outsource srid ?
            geom.srid = 4326
            return geom

        if not all([isinstance(val, (float, int,))
                    for val in [xmin, ymin, xmax, ymax]]):
            raise ValueError("expecting number as coordinates")
        if not (limit is None or (isinstance(limit, int) and limit >= 0)):
            raise ValueError("limit must be an int and >= 0 or None")

        if not (-180 <= xmin <= 180 and -180 <= xmax <= 180):
            raise ValueError("xmin and xmax must be between [-180, 180]")
        if not (-90 <= ymin <= 90 and -90 <= ymax <= 90):
            raise ValueError("ymin and ymax must be between [-90, 90]")
        if not (ymin <= ymax):
            raise ValueError("ymin and ymax must be between [-90, 90]")

        polys = []
        for j in range(2):
            for i in range(4):
                q_ymin, q_ymax = j*90 - 90, j*90
                q_xmin, q_xmax = i*90 - 180, i*90 - 90

                if ymax < q_ymin or q_ymax < ymin:
                    continue
                c_ymin = max(q_ymin, ymin)
                c_ymax = min(ymax, q_ymax)

                # bounding_box crosses 180° meridian
                if xmax < xmin:
                    if xmax > q_xmin:
                        geom = create_poly(
                            q_xmin, c_ymin, max(q_xmax, xmax), c_ymax)
                        polys.append(geom)

                    if xmin < q_xmax:
                        geom = create_poly(
                            min(xmin, q_xmin), c_ymin, q_xmax, c_ymax)
                        polys.append(geom)
                else:
                    if xmax < q_xmin or q_xmax < xmin:
                        continue
                    c_xmin = max(q_xmin, xmin)
                    c_xmax = min(xmax, q_xmax)
                    geom = create_poly(c_xmin, c_ymin, c_xmax, c_ymax)
                    polys.append(geom)

        covered_by = ["ST_CoveredBy(a.point,ST_GeomFromText('{0}'))"
                      .format(geom.ewkt) for geom in polys]
        from_clause = str(self.query)
        where_clause = " OR ".join(covered_by)
        limit_clause = f" LIMIT {limit}" if limit is not None else ""
        query = ('SELECT a.* FROM ({0}) AS a WHERE {1}{2}'
                 .format(from_clause, where_clause, limit_clause))

        return self.raw(query)


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

    objects = BaseInfosQuerySet.as_manager()

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
        return '{0}: ({1}, {2})'.format(
            type(self).__name__,
            self.mmsi,
            str(self.time)
        )


class ShipInfos(BaseInfos):
    """Concrete class for the table holding the ship informations sent by AIS"""
    mmsi = models.IntegerField(primary_key=True)


class MessageQuerySet(BaseInfosQuerySet):
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
             escape='\\', quote='\"') -> Tuple[int, int]:
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
