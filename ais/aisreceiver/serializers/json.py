"""Custom JSON serializer

This will encode/decode usefull types to use with redis for example.

datetime <-> {"__datetime__":true, "utctimestamp":someutctimestamp}
Point <-> {"__point__":true, "coords":[lon,lat]}
"""
from datetime import datetime, timezone
import json

from django.contrib.gis.geos import Point


def redis_object_hook(d):
    """Custom hook to use with JsonDecoder"""
    if '__datetime__' in d:
        return datetime.fromtimestamp(d['utctimestamp'], tz=timezone.utc)
    if '__point__' in d:
        return Point(*d['coords'])
    return d


def default_redis_encoder(o):
    """Default encoder to use with JsonEncoder"""
    if isinstance(o, datetime):
        return dict(__datetime__=True, utctimestamp=o.timestamp())
    if isinstance(o, Point):
        return dict(__point__=True, coords=o.coords)
    return json.JSONEncoder.default(o)


# custom_redis_decoder = json.JSONDecoder(object_hook=redis_object_hook)
# custom_redis_encoder = json.JSONEncoder(default=default_redis_encoder)
