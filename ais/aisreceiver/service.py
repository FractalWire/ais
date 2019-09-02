"""Module used to manage aisreceiver service"""
from __future__ import annotations
from typing import List
from time import sleep
import json

from core.models import Message
from core.serializers.json import redis_object_hook

from .endpoints import aishubapi
from .app_settings import POSTGRES_UPDATE_WINDOW
from .redisclient import redis_client, pipeline_client

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
    #    - flush redis aismessages
    while run:

        messages_before = Message.objects.count()
        logger.debug("starting database update")
        messages = make_bulk_messages()
        # TODO: Need redis lock before that, to avoid potential message loss
        redis_client.delete('aismessages')

        messages_len = len(messages)
        logger.debug('starting bulk_create')
        Message.objects.bulk_create(messages, ignore_conflicts=True)

        logger.info('database updated')
        messages_after = Message.objects.count()

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
                  .values(*Message.infos_keys()))
    redis_client.flushdb()  # TODO: probably not needed
    for infos in last_infos:
        pipeline_client.set(f'infos:{infos["mmsi"]}', json.dumps(infos))
    pipeline_client.execute()


def make_bulk_messages() -> List[Message]:
    """Creates a message list for following batch processing to the database
    based on redis 'infos:' and 'position:'"""

    messages = []

    logger.debug('fetching data from redis')

    messages_redis = redis_client.hgetall('aismessages')
    logger.debug('making bulk_messages')
    for message_redis in messages_redis.values():
        message = Message(
            **json.loads(message_redis, object_hook=redis_object_hook)
        )
        messages.append(message)

    return messages
