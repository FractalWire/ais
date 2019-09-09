"""Custom msgpack serializer

This will encode/decode usefull types to use with redis for example.

datetime <-> {"__datetime__":true, "utctimestamp":someutctimestamp}
Point <-> {"__point__":true, "coords":[lon,lat]}
"""
from __future__ import annotations
from typing import Dict, Any
from datetime import datetime, timezone

from django.contrib.gis.geos import Point


def object_decoder(d: Dict[bytes, Any]) -> Any:
    """Custom hook to use with unpackb"""
    if '__datetime__' in d:
        return datetime.fromtimestamp(d['utctimestamp'], tz=timezone.utc)
    if '__point__' in d:
        return Point(*d['coords'])
    return d


def default_encoder(o: Any) -> dict[str, Any]:
    """Default encoder to use with packb"""
    if isinstance(o, datetime):
        return dict(__datetime__=True, utctimestamp=o.timestamp())
    if isinstance(o, Point):
        return dict(__point__=True, coords=o.coords)
    return o


def default_key_encoder(o: Any) -> dict[str, Any]:
    """Default encoder to use for hash key encoding"""
    if isinstance(o, datetime):
        return o.timestamp()
    if isinstance(o, Point):
        return o.coords
    return o
