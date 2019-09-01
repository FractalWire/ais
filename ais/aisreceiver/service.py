"""Module used to manage aisreceiver service"""
from __future__ import annotations
from typing import List
from time import sleep
import json

from core.models import Message
from .endpoints import aishubapi
from .aismessage import Infos, Position, default_infos, infos_keys
# from .buffer import position_buffer, infos_buffer, buffer_lock
from .app_settings import POSTGRES_UPDATE_WINDOW
from .redisclient import redis_client, pipeline_client
from .serializers.json import redis_object_hook

import logging
from logformat import StyleAdapter

logger = StyleAdapter(logging.getLogger(__name__))


run = True


def start() -> None:

    logger.info("==== Starting AIS service ====")

    # 1) init redis
    init_redis()
    logger.info("redis initialized")

    # 2) launch endpoint listeners
    aishubapi.start()
    logger.info("aishubapi endpoints started")
    logger.info("==============================")

    sleep(10)  # give endpoints time to start for immediate update

    # 3) every X minutes :
    #    - update database from redis
    while run:

        logger.debug("starting database update")
        messages_before = Message.objects.count()
        messages = make_bulk_messages()
        messages_len = len(messages)
        Message.objects.bulk_create(messages, ignore_conflicts=True)
        messages_after = Message.objects.count()

        logger.info('database updated')

        # TODO: Maybe only useful in DEBUG mode...
        new_messages = messages_after-messages_before
        logger.debug("{} new messages added to the database, {} discarded",
                     new_messages, messages_len-new_messages)

        logger.info("------------------------------")
        sleep(POSTGRES_UPDATE_WINDOW)


def stop() -> None:
    pass


def init_redis() -> None:
    """Initialises redis with existing corresponding Message fields from
    the database"""
    last_infos = (Message.objects.distinct('mmsi')
                  .order_by('mmsi', '-time')
                  .values(*infos_keys))
    redis_client.flushdb()
    for infos in last_infos:
        pipeline_client.set(f'infos:{infos["mmsi"]}', json.dumps(infos))
    pipeline_client.execute()


def make_bulk_messages() -> List[Message]:
    """Creates a message list for following batch processing to the database
    based on redis 'infos:' and 'position:'"""

    messages = []

    # TODO: use scan instead MAYBE, check performance before
    infos_keys_redis = redis_client.keys('infos:*')
    position_keys_redis = redis_client.keys('position:*')

    infos_redis = redis_client.mget(infos_keys_redis)
    position_redis = redis_client.mget(position_keys_redis)

    # TODO: are those buffers really needed ? extra work ?
    mmsi_start = len('infos:')
    infos_buffer = {
        k[mmsi_start:]: json.loads(v, object_hook=redis_object_hook)
        for k, v in zip(infos_keys_redis, infos_redis)
    }
    mmsi_start = len('position:')
    position_buffer = {
        k[mmsi_start:]: json.loads(v, object_hook=redis_object_hook)
        for k, v in zip(position_keys_redis, position_redis)
    }

    for mmsi, position in position_buffer.items():
        infos = mmsi in infos_buffer and infos_buffer[mmsi] or default_infos
        message = Message(
            **{
                **infos,
                **position
            }
        )
        messages.append(message)

    return messages
