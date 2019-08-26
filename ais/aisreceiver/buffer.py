from __future__ import annotations
from typing import Dict, List
import threading

from .aismessage import Infos, Position

buffer_lock: threading.Lock = threading.Lock()

"""Dictionary that holds the last known infos for each AIS"""
infos_buffer: Dict[str, Infos] = dict()


def add_infos(infos: List[Infos]) -> None:
    """Add a list of infos from incoming messages"""
    for inf in infos:
        infos_buffer[inf.mmsi] = inf


"""Dictionary that holds the last postions for each AIS, updated every
_POSITIONS_UPDATE_TIMER"""
position_buffer: Dict[str, Positions] = dict()


def flush_positions() -> None:
    """Deletes all stored positions in positions_dict. Should be called every
    _POSITIONS_UPDATE_TIMER"""
    position_buffer.clear()


def add_positions(positions: List[Position]) -> None:
    """Add a list of positions to the positions_dict from incoming messages"""
    for pos in positions:
        position_buffer[pos.mmsi] = pos
