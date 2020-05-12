"""Module used to manage aisreceiver service"""
from __future__ import annotations
from typing import Set, Any
from time import sleep
import io
import threading
import queue
# import shutil

from core.models import copy_csv
from core import service

from .endpoints.aishubapi import AisHubService
from .app_settings import POSTGRES_WINDOW
from . import aisbuffer

import logging
from logformat import StyleAdapter

logger = StyleAdapter(logging.getLogger(__name__))


class AisService(service.BaseService):

    def __init__(self):
        super().__init__()
        self.subscribed_channels: Set[queue.Queue] = {}

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
        while True:
            try:
                _, evt = self.evt_channel.get(timeout=POSTGRES_WINDOW)
                if evt == service.Event.STOP:
                    break
            except queue.Empty:
                pass

            # TODO: sleep time do not take into account update_db process time
            self.update_db()

            self.publish((1, service.Event.DB_UPDATED))

        # 3) stop and wait for aishub_service to terminate
        aishub_service.stop()
        aishub_service.thread.join()

        logger.info("==== AIS service stopped ====")

    def subscribe(self, channel: queue.Queue) -> None:
        self.subscribed_channels.add(channel)

    def unsubscribe(self, channel: queue.Queue) -> None:
        self.subscribed_channels.discard(channel)

    def publish(self, val: Any) -> None:
        for channel in self.subscribed_channels:
            channel.put(val)

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
        new_messages, new_shipinfos = copy_csv(f)
        f.close()

        # TODO: Maybe only useful in DEBUG mode...
        logger.info("{} new messages added to the database, {} discarded",
                    new_messages, total_messages-new_messages)
        logger.info("{} new ship infos added to the database, {} discarded",
                    new_shipinfos, total_messages-new_shipinfos)

        logger.info('database updated')
        logger.info("------------------------------")
