from __future__ import annotations
import threading
import queue

from core.service import BaseService, ServiceEvent
from .app_settings import GEOSERVER_WINDOW
from .models import ShipGeometries

import logging
from logformat import StyleAdapter

logger = StyleAdapter(logging.getLogger(__name__))


class GeoserverService(BaseService):

    def run(self) -> None:
        logger.info("geoserver service started")

        evt = None
        while True:
            if evt == ServiceEvent.STOP:
                break

            elif evt == ServiceEvent.DB_UPDATED:
                logger.debug("starting ship geometries update")
                modified_cnt = ShipGeometries.objects.update_or_create_all_geometries()
                logger.info("{} geometries modified", modified_cnt)
                logger.info('ship geometries updated')
                logger.info("------------------------------")

            evt = self.get_channel_evt(timeout=GEOSERVER_WINDOW)
