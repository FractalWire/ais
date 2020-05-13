from __future__ import annotations
from typing import Set, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from queue import PriorityQueue


class PubSubMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscribed_channels: Set[PriorityQueue] = set()

    def subscribe(self, channel: PriorityQueue) -> None:
        self._subscribed_channels.add(channel)

    def unsubscribe(self, channel: PriorityQueue) -> None:
        self._subscribed_channels.discard(channel)

    def publish(self, val: Any) -> None:
        for channel in self._subscribed_channels:
            channel.put(val)
