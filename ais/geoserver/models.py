from __future__ import annotations
from core.models import ShipInfos
import datetime
from typing import List, Tuple

from django.contrib.gis.db import models
from django.db.models import F

import logging
from logformat import StyleAdapter

logger = StyleAdapter(logging.getLogger(__name__))


class GeometryManager(models.Manager):
    def apply_update(self, geom: ShipGeometries) -> ShipGeometries:
        def set_shape(geom: ShipGeometries) -> ShipGeometries:
            geom.wkt_shape = geom.mmsi.ship_wkt
            return geom

        def set_path(geom: ShipGeometries) -> ShipGeometries:
            # TODO: implement that
            return geom

        def set_dimensions(geom: ShipGeometries) -> ShipGeometries:
            geom.length = geom.mmsi.length
            geom.width = geom.mmsi.width
            return geom

        def set_last_update(geom: ShipGeometries) -> ShipGeometries:
            geom.last_update = geom.mmsi.time
            return geom

        return set_last_update(set_dimensions(set_path(set_shape(geom))))

    def ship_without_geometries(self) -> models.QuerySet:
        return ShipInfos.objects.filter(shipgeometries__isnull=True)

    def update_or_create_all_geometries(self) -> None:
        # TODO: very slow, need some optimisation...
        def missing_geometries() -> List[ShipGeometries]:
            return [self.apply_update(
                self.model(mmsi=ship, last_update=datetime.datetime(1, 1, 1)))
                for ship in self.ship_without_geometries()]

        def need_update() -> List[ShipGeometries]:
            return [self.apply_update(geom) for geom in
                    ShipGeometries.objects.exclude(mmsi__time=F('last_update'))]

        logger.debug("geom update started")
        geom_to_update = need_update()
        logger.debug("geom update end fetch")
        self.bulk_update(geom_to_update,
                         fields=[f.name for f in self.model._meta.get_fields()
                                 if f.name != 'mmsi'],
                         batch_size=1000)
        logger.debug("geom update finished")

        logger.debug("geom create started")
        geom_to_create = missing_geometries()
        logger.debug("geom create end fetch")
        self.bulk_create(geom_to_create, batch_size=1000)
        logger.debug("geom create finished")

        return len(geom_to_create) + len(geom_to_update)


class ShipGeometries(models.Model):
    """Stores every ship related geometries useful for geoserver rendering"""
    mmsi = models.OneToOneField(ShipInfos, primary_key=True,
                                on_delete=models.CASCADE, db_column='mmsi')
    length = models.IntegerField(null=False, blank=True, default=0)
    width = models.IntegerField(null=False, blank=True, default=0)
    wkt_shape = models.CharField(max_length=256, blank=True, default='')
    path = models.LineStringField(geography=True, null=True, blank=True,
                                  default=None)
    last_update = models.DateTimeField()

    objects = GeometryManager()
