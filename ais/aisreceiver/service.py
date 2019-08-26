"""Module used to manage aisreceiver service"""
from time import sleep

import aisreceiver.endpoints.aishubapi as aishubapi
from .models import Message
from .aismessage import Infos, Position, default_infos, infos_keys
from .buffer import position_buffer, infos_buffer


def start():

    # 1) launch endpoint listeners
    # 2) init infos_dict
    # 3) every X minutes :
    #    - update database from positions_dict and infos dict
    #    - flush positions_dict

    aishubapi.start()


def stop():
    pass


def init_infos_dict() -> None:
    """Initialises infos_dict with existing corresponding Message fields in 
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
