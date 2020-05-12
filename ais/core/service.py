from __future__ import annotations
import abc
import threading
import queue
from enum import IntFlag


class Event(IntFlag):
    STOP = 0
    DB_UPDATED = 1


class BaseService(abc.ABC):

    def __init__(self) -> None:
        self.thread = threading.Thread(target=self.run)
        self.evt_channel = queue.PriorityQueue()

    def start(self) -> None:
        """Start service"""
        self.thread.start()

    @abc.abstractmethod
    def run(self) -> None:
        """The process to run as a service"""
        pass

    def stop(self) -> None:
        """Start service"""
        self.evt_channel.put((0, Event.STOP))
