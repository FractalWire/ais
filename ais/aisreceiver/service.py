"""Module used to manage aisreceiver service"""
from __future__ import annotations
from typing import List, Iterator
from time import sleep
import json

from core.models import Message
from core.serializers.json import redis_object_hook

from .endpoints import aishubapi
from .app_settings import POSTGRES_WINDOW
from .redisclient import redis_client, pipeline_client

import logging
from logformat import StyleAdapter

logger = StyleAdapter(logging.getLogger(__name__))


run = True


def start() -> None:

    logger.info("==== Starting AIS service ====")

    # 1) init redis
    init_redis()

    # 2) launch endpoint listeners
    aishubapi.start()

    sleep(10)  # give endpoints time to start for immediate update

    logger.info("aishubapi endpoints started")
    logger.info("==============================")

    # 3) every X minutes :
    #    - update database from redis
    #    - flush redis aismessages
    while run:
        update_db()
        # TODO: sleep time do not take into account update_db process time
        sleep(POSTGRES_WINDOW)


def stop() -> None:
    pass


def init_redis() -> None:
    """Initialises redis with existing corresponding Message fields from
    the database"""
    redis_client.flushdb()  # TODO: probably not needed

    logger.debug('starting Redis initialization')
    last_infos = (Message.objects.distinct('mmsi')
                  .order_by('mmsi', '-time')
                  .values(*Message.infos_keys()))
    logger.debug('infos fetched from database')
    for infos in last_infos:
        pipeline_client.set(f'infos:{infos["mmsi"]}', json.dumps(infos))
    pipeline_client.execute()

    logger.info("redis initialized")


def message_generator(batch_size, redis_count: int = 100) -> Iterator[List[Message]]:
    """Generate Message model from Redis 'aismessages:' keys and delete those
    keys from Redis once generated"""
    messages = []
    total_messages = 0
    cursor = 0
    i = 0
    loops_before_yield = batch_size // redis_count
    while True:
        cursor, redis_messages = redis_client.hscan(
            'aismessages',
            cursor=cursor,
            count=redis_count
        )
        if not redis_messages:
            return
        redis_client.hdel('aismessages', *redis_messages.keys())

        for redis_message in redis_messages.values():
            message = Message(
                **json.loads(redis_message, object_hook=redis_object_hook)
            )
            messages.append(message)

        i += 1
        if i >= loops_before_yield:
            total_messages += len(messages)
            yield (total_messages, messages,)
            messages = []
            i = 0

        if cursor == 0:
            return


def update_db() -> None:
    """Update the database using messages stored in redis"""

    logger.debug("starting database update")
    messages_before = Message.objects.count()

    logger.debug('bulk_create using message_generator')
    batch_size = 1000
    total_messages = 0
    for total_messages, messages in message_generator(batch_size):
        Message.objects.bulk_create(messages, ignore_conflicts=True)

    messages_after = Message.objects.count()

    # TODO: Maybe only useful in DEBUG mode...
    new_messages = messages_after-messages_before
    logger.debug("{} new messages added to the database, {} discarded",
                 new_messages, total_messages-new_messages)

    logger.info('database updated')
    logger.info("------------------------------")
