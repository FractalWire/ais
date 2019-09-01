from __future__ import annotations

from typing import NamedTuple
from datetime import datetime

from django.contrib.gis.geos import Point


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


default_infos = Infos('DEFAULT')
infos_keys = default_infos._asdict().keys()


class Position(NamedTuple):
    """Position information sent by the vessel via AIS"""
    mmsi: str
    time: datetime
    # longitude: float
    # latitude: float
    point: Point
    valid_position: bool = True
    cog: int = 360.0
    sog: float = 102.4
    heading: int = 511
    pac: bool = 0
    rot: int = 128
    navstat: int = 15
    # infos: Infos = None


default_position = Position('DEFAULT', datetime.fromtimestamp(0), Point(0, 0))
position_keys = default_position._asdict().keys()
