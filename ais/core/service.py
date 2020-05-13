from __future__ import annotations
from typing import TYPE_CHECKING, List
import abc
import threading
import queue
from enum import IntFlag

import logging
from logformat import StyleAdapter

logger = StyleAdapter(logging.getLogger(__name__))

if TYPE_CHECKING:
    from core.mixins import PubSubMixin


class ServiceEvent(IntFlag):
    STOP = 0
    DB_UPDATED = 1


class BaseService(abc.ABC):
    def __init__(self, channel_subscriptions: List[PubSubMixin] = list()) -> None:
        self.thread = threading.Thread(target=self.run)
        self.evt_channel = queue.PriorityQueue()

        for pubsub in channel_subscriptions:
            pubsub.subscribe(self.evt_channel)

    def start(self) -> None:
        """Start service"""
        self.thread.start()

    @abc.abstractmethod
    def run(self) -> None:
        """The process to run as a service"""
        pass

    def get_channel_evt(self, timeout: int = None) -> ServiceEvent:
        try:
            _, evt = self.evt_channel.get(timeout=timeout)
        except queue.Empty:
            # logger.debug("service: no events before timeout")
            evt = None
        return evt

    def stop(self) -> None:
        """Start service"""
        self.evt_channel.put((0, ServiceEvent.STOP))
