"""Module used to manage aisreceiver service"""
from __future__ import annotations
from typing import Set, Any
from time import sleep
import io
import threading
import queue
# import shutil

from core.models import copy_csv
from core.service import BaseService, ServiceEvent
from core.mixins import PubSubMixin

from .endpoints.aishubapi import AisHubService
from .app_settings import POSTGRES_WINDOW, KEEP_SHIPINFOS_HISTORY
from . import aisbuffer

import logging
from logformat import StyleAdapter

logger = StyleAdapter(logging.getLogger(__name__))


class AisService(PubSubMixin, BaseService):

    def run(self) -> None:
        logger.info("==== Starting AIS service ====")

        # 1) launch endpoint listeners
        aishub_service = AisHubService()
        aishub_service.start()

        sleep(10)  # give endpoints time to start for immediate update

        logger.info("==============================")

        # 2) every X minutes :
        #    - update database from AisBuffer
        #    - flush AisBuffer
        evt = None
        while True:
            if evt == ServiceEvent.STOP:
                break

            # TODO: sleep time do not take into account update_db process time
            self.update_db()

            self.publish((1, ServiceEvent.DB_UPDATED))
            evt = self.get_channel_evt(timeout=POSTGRES_WINDOW)

        # 3) stop and wait for aishub_service to terminate
        aishub_service.stop()
        aishub_service.thread.join()

        logger.info("==== AIS service stopped ====")

    def update_db(self) -> None:
        """Update the database using messages stored in buffer"""

        logger.debug("starting database update")

        f = io.StringIO()
        batch_size = 10000
        logger.debug('preparing csv file for COPY using message_generator')
        total_messages = aisbuffer.messages.prepare_csv(f, batch_size)

        # f.seek(0)
        # with open('copy.csv', 'w') as file_copy:
        #     shutil.copyfileobj(f, file_copy)

        logger.debug('starting to COPY')
        f.seek(0)
        new_messages, new_shipinfos = copy_csv(
            f, keep_history=KEEP_SHIPINFOS_HISTORY)
        f.close()

        # TODO: Maybe only useful in DEBUG mode...
        logger.info("{} new messages added to the database, {} discarded",
                    new_messages, total_messages-new_messages)
        logger.info("{} new ship infos added to the database, {} discarded",
                    new_shipinfos, total_messages-new_shipinfos)

        logger.info('core database updated')
        logger.info("------------------------------")
