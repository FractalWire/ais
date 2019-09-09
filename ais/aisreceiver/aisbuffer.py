from __future__ import annotations
from typing import Dict, List, Any, Iterator, Callable
import threading
import json
import msgpack

# from core.models import Message
from core.serializers import msgpack as ms
from core.serializers import json as js
from core.serializers import csv as cs

AisData = Dict[str, Any]


class AisBuffer:
    """A buffer used to store AIS data before database update
    TODO: Might be too generic..."""

    def __init__(
            self,
            keyformat: Callable[[AisData], str],
            serialize: Callable[[AisData], Any] = lambda x: x,
            deserialize: Callable[[Any], AisData] = lambda x: x
    ) -> None:
        self.lock = threading.Lock()
        self.data: AisData = dict()
        self.keyformat = keyformat
        self.serialize = serialize
        self.deserialize = deserialize

    def generator(self, batch_size: int = 1000) -> Iterator[int, List[AisData]]:
        """Generate and remove batch_size data from self.data"""
        data = []
        i = 0
        self.lock.acquire()
        while self.data:
            _, d = self.data.popitem()
            data.append(self.deserialize(d))

            i += 1
            if i % batch_size == 0:
                self.lock.release()
                yield (i, data,)
                data.clear()
                self.lock.acquire()

        self.lock.release()
        yield (i, data,)
        data.clear()

    def update(self, data: List[AisData], batch_size: int = 1000) -> None:
        """Update the buffer with data in batch"""
        pass_num = len(data)//batch_size + 1
        for i in range(pass_num):
            first = i*batch_size
            last = min(first+batch_size, len(data))
            with self.lock:
                for d in data[first:last]:
                    key = self.keyformat(d)

                    if key not in self.data:
                        self.data[key] = self.serialize(d)


# TODO: Organize that better

def json_serializer(message: AisData) -> str:
    return json.dumps(message, default=js.default_encoder, use_bin_type=True)


def json_deserializer(json_object: str) -> AisData:
    return json.loads(json_object, object_hook=js.object_decoder)


def msgpack_serializer(message: AisData) -> bytes:
    return msgpack.packb(message, default=ms.default_encoder, use_bin_type=True)


def msgpack_to_csv_deserializer(msgpack_object: bytes) -> Dict[str, Any]:
    message = msgpack.unpackb(msgpack_object,
                              object_hook=ms.object_decoder,
                              raw=False)
    return {k: cs.default_encoder(v) for k, v in message.items()}


def messages_keyformat(data: AisData) -> str:
    return '{0}:{1}'.format(data['mmsi'], data['time'].timestamp())


messages = AisBuffer(keyformat=messages_keyformat,
                     serialize=msgpack_serializer,
                     deserialize=msgpack_to_csv_deserializer)

# def last_messages_keyformat(data: AisData) -> str:
#     return '{0}'.format(data['mmsi'])


# def last_messages_keep_onconflict(current: AisData, new: AisData) -> bool:
#     return current['time'] < new['time']

# last_messages = AisBuffer(keyformat=last_messages_keyformat,
#                           serialize=msgpack_serializer,
#                           deserialize=msgpack_deserializer,
#                           keep_onconflict=last_messages_keep_onconflict)
