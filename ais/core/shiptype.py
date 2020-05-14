from __future__ import annotations
from typing import Generator, Tuple
from collections import namedtuple

ShipType = namedtuple('ShipType',
                      'type short_name name summary details')
range_type = [
    [(0, 19), ShipType(0, 'unspecified', 'unspecified', 'reserved', '')],
    [(20, 28), ShipType(0, 'wing', 'wing in ground', 'wing in grnd', '')],
    [(29, 29), ShipType(0, 'sar', 'search and rescue', 'SAR aircraft', '')],
    [(30, 30), ShipType(0, 'fishing', 'fishing', 'fishing', '')],
    [(31, 32), ShipType(0, 'tug', 'tug', 'tug', '')],
    [(33, 33), ShipType(0, 'special', 'special craft', 'dredger', '')],
    [(34, 34), ShipType(0, 'special', 'special craft', 'dive vessel', '')],
    [(35, 35), ShipType(0, 'special', 'special craft', 'military ops', '')],
    [(36, 36), ShipType(0, 'sailing', 'sailing vessel', 'sailing vessel', '')],
    [(37, 37), ShipType(0, 'pleasure', 'pleasure craft', 'pleasure craft', '')],
    [(38, 39), ShipType(0, 'unspecified', 'unspecified', 'reserved', '')],
    [(40, 49), ShipType(0, 'highspeed', 'high-speed craft', 'high-speed craft', '')],
    [(50, 50), ShipType(0, 'special', 'special craft', 'pilot vessel', '')],
    [(51, 51), ShipType(0, 'sar', 'search and rescue', 'SAR', '')],
    [(52, 52), ShipType(0, 'tug', 'tug', 'tug', '')],
    [(53, 53), ShipType(0, 'special', 'special craft', 'port tender', '')],
    [(54, 54), ShipType(0, 'special', 'special craft', 'anti-pollution', '')],
    [(55, 55), ShipType(0, 'special', 'special craft', 'law enforce', '')],
    [(56, 57), ShipType(0, 'special', 'special craft', 'local vessel', '')],
    [(58, 58), ShipType(0, 'special', 'special craft', 'medical trans', '')],
    [(59, 59), ShipType(0, 'special', 'special craft', 'special craft', '')],
    [(60, 69), ShipType(0, 'passenger', 'passenger', 'passenger', '')],
    [(70, 70), ShipType(0, 'cargo', 'cargo', 'cargo', '')],
    [(71, 71), ShipType(0, 'cargo', 'cargo', 'cargo - hazard A (major)', '')],
    [(72, 72), ShipType(0, 'cargo', 'cargo', 'cargo - hazard B', '')],
    [(73, 73), ShipType(0, 'cargo', 'cargo', 'cargo - hazard C (minor)', '')],
    [(74, 74), ShipType(0, 'cargo', 'cargo', 'cargo - hazard D (recognizable)', '')],
    [(75, 79), ShipType(0, 'cargo', 'cargo', 'cargo', '')],
    [(80, 80), ShipType(0, 'tanker', 'tanker', 'tanker', '')],
    [(81, 81), ShipType(0, 'tanker', 'tanker', 'tanker - hazard A (major)', '')],
    [(82, 82), ShipType(0, 'tanker', 'tanker', 'tanker - hazard B', '')],
    [(83, 83), ShipType(0, 'tanker', 'tanker', 'tanker - hazard C (minor)', '')],
    [(84, 84), ShipType(0, 'tanker', 'tanker', 'tanker - hazard D (recognizable)', '')],
    [(85, 89), ShipType(0, 'tanker', 'tanker', 'tanker', '')],
    [(90, 99), ShipType(0, 'other', 'other', 'other', '')],
]


def shiptype_generator() -> Generator[ShipType, None, None]:
    for r, t in range_type:
        for i in range(r[0], r[1]+1):
            yield ShipType(i, *t[1:])
