"""Custom csv serializer

This will encode/decode usefull types to use with SQL COPY for example

datetime <-> "isodatetime":someisodatetime
Point <-> "hexpoint":somepoint_hexewkb
"""
from __future__ import annotations
from typing import Dict, Any
from datetime import datetime

from django.contrib.gis.geos import Point


def default_encoder(o: Any) -> Dict[str, Any]:
    """Default encoder for csv. The output can be used with a DictWriter
    instance before SQL COPY"""
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, Point):
        return o.hexewkb.decode()
    if isinstance(o, str):
        # TODO: something better for escaping quote here
        return '"{0}"'.format(o.replace('"', "'"))
    return o
