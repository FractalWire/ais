from __future__ import annotations
from typing import Dict, List
from typing import NamedTuple
from datetime import datetime

from django.contrib.gis.geos import Point

from .models import Message


class Infos(NamedTuple):
    """Various informations sent by the vessel via AIS"""
    mmsi: str
    imo: str = ''
    callsign: str = ''
    name: str = ''
    ship_type: int = 0
    dim_bow: int = 0
    dim_stern: int = 0
    dim_port: int = 0
    dim_starboard: int = 0
    eta: datetime = None
    draught: float = 0.
    destination: str = ''

    def is_default(self) -> bool:
        """Check if the instance has default parameters
        TODO: Enhanced that to avoid repeated creation of a default object"""
        return self[1:] == Infos("DEFAULT")[1:]


class Position(NamedTuple):
    """Position information sent by the vessel via AIS"""
    mmsi: str
    time: datetime
    # longitude: float
    # latitude: float
    point: Point
    cog: int = 360.0
    sog: float = 102.4
    heading: int = 511
    pac: bool = 0
    rot: int = 0
    navstat: int = 15
    infos: Infos = None


# TODO: Put that in a config file maybe
_POSITIONS_UPDATE_TIMER = 5 * 60  # in seconds

"""Dictionary that holds the last known infos for each AIS"""
infos_dict: Dict[str, Infos] = dict()


def init_infos_dict() -> None:
    """Initialises infos_dict with existing corresponding Message fields in 
    the database"""

    default_infos_keys = Infos('DEFAULT')._asdict().keys()

    last_infos = (Message.objects.distinct('mmsi')
                  .order_by('mmsi', '-time')
                  .values(*default_infos_keys))
    infos_dict.clear()
    for infos in last_infos:
        infos_dict[infos['mmsi']] = Infos(**infos)


def add_infos(infos: Infos) -> None:
    """Add an infos from a new incoming message"""
    # if not infos.is_default():
    infos_dict[infos.mmsi] = infos


"""Dictionary that holds the last postions for each AIS, updated every
_POSITIONS_UPDATE_TIMER"""
positions_dict: Dict[str, Positions] = dict()


def flush_positions() -> None:
    """Deletes all stored positions in positions_dict. Should be called every
    _POSITIONS_UPDATE_TIMER"""
    positions_dict.clear()


def add_position(position: Position) -> None:
    """Add a position to the positions_dict if the position mmsi does not
    already exists in the dictionary"""
    if not position.mmsi in positions_dict:
        positions_dict[position.mmsi] = position


def make_batch_messages() -> List[Message]:
    """Creates a message list for following batch processing to the database
    based on infos_dict and positions_dict"""

    default_infos = Infos('DEFAULT')
    messages = []

    for mmsi, position in positions_dict.items():
        infos = mmsi in infos_dict and infos_dict[mmsi] or default_infos
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
        # message = Message(**{**position, **infos})
        messages.append(message)

    return messages
