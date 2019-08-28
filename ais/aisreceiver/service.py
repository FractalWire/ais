"""Module used to manage aisreceiver service"""
from time import sleep

from core.models import Message
from .endpoints import aishubapi
from .aismessage import Infos, Position, default_infos, infos_keys
from .buffer import position_buffer, infos_buffer, buffer_lock

# Update interval to store the latest position received
# TODO: put that in a config file maybe
MESSAGE_UPDATE_WINDOW = 5*60  # in seconds


run = True


def start() -> None:

    # 1) launch endpoint listeners
    aishubapi.start()

    # 2) init infos_buffer
    with buffer_lock:
        init_infos_buffer()

    # 3) every X minutes :
    #    - update database from position_buffer and infos_buffer
    #    - flush positions_buffer

    while run:

        with buffer_lock:
            messages = make_batch_messages()
            Message.objects.batch_create(messages)
            position_buffer.clear()

        sleep(MESSAGE_UPDATE_WINDOW)


def stop() -> None:
    pass


def init_infos_buffer() -> None:
    """Initialises infos_buffer with existing corresponding Message fields from 
    the database"""

    last_infos = (Message.objects.distinct('mmsi')
                  .order_by('mmsi', '-time')
                  .values(*infos_keys))
    infos_buffer.clear()
    for infos in last_infos:
        infos_buffer[infos['mmsi']] = Infos(**infos)


def make_batch_messages() -> List[Message]:
    """Creates a message list for following batch processing to the database
    based on infos_dict and positions_dict"""

    # default_infos = Infos('DEFAULT')
    messages = []

    for mmsi, position in position_buffer.items():
        infos = mmsi in infos_buffer and infos_buffer[mmsi] or default_infos
        message = Message(
            mmsi=mmsi
            time=position.time
            point=position.point
            cog=position.cog
            sog=position.sog
            heading=position.heading
            pac=position.pac
            rot=position.rot
            navstat=position.navstat

            imo=infos.imo
            callsign=infos.callsign
            name=infos.name
            ship_type=infos.ship_type
            dim_bow=infos.dim_bow
            dim_stern=infos.dim_stern
            dim_port=infos.dim_port
            dim_starboard=infos.dim_starboard
            eta=infos.eta
            draught=infos.draught
            destination=infos.destination
        )
        # TODO: Try that
        # message = Message(**{**infos, **position})
        messages.append(message)

    return messages
