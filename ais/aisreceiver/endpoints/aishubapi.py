"""This module manages the interaction with AISHub API
https://www.aishub.net/api"""
from __future__ import annotations
from typing import List, Dict, Tuple
import sys
import requests
import gzip
import json
import threading
from io import BytesIO
from enum import Flag, IntFlag
from datetime import datetime, timezone

from django.contrib.gis.geos import Point
import redis

from aisreceiver.aismessage import Infos, Position, infos_keys, position_keys
from aisreceiver.app_settings import POSITION_EXPIRE_TTL, AISHUBAPI_UPDATE_WINDOW
from aisreceiver.redisclient import redis_client, pipeline_client
from aisreceiver.serializers.json import default_redis_encoder

import logging
from logformat import StyleAdapter

logger = StyleAdapter(logging.getLogger(__name__))


class AisHubError(Exception):
    """Raised when an error occurred while trying to get last data"""
    pass


class Format(IntFlag):
    AIS_ENCODING = 0
    HUMAN_READABLE = 1


class Output(Flag):
    XML = 'xml'
    JSON = 'json'
    CSV = 'csv'


class Compression(IntFlag):
    NONE = 0
    ZIP = 1
    GZIP = 2
    BZIP2 = 3


URL = 'http://data.aishub.net/ws.php?'

format_ = Format.AIS_ENCODING
output = Output.JSON
compression = Compression.GZIP

parameters = {
    'username': 'AH_2575_E34F276C',
    'format': format_.value,
    'output': output.value,
    'compress': compression.value,

    # optional parameters
    # 'latmin': '',
    # 'latmax': '',
    # 'lonmin': '',
    # 'lonmax': '',
    # 'mmsi': '',
    # 'imo': '',
}


def _fetch_last_data() -> List[Dict[str, str]]:
    """Fetch last data via AisHubAPI"""
    data = []
    if compression != Compression.GZIP:
        raise Exception(f"{compression} compression not supported yet,"
                        " please use another compression method.")
    if output != Output.JSON:
        raise Exception(f"{output} output not supported yet,"
                        " please use another output format.")
    try:
        response = requests.get(URL, params=parameters)
        gz = gzip.GzipFile(fileobj=BytesIO(response.content))
        data = json.loads(gz.read())
    except Exception as err:
        logger.error('Error when trying to retrieve AisHub last data: {}', err)

    if len(data) < 1:
        raise AisHubError('Failed to fetch AisHub data properly')
    if data[0]['ERROR']:
        raise AisHubError(
            'ERROR_MESSAGE: {0}'.format(data[0]['ERROR_MESSAGE'])
        )
    if len(data) < 2:
        raise AisHubError('Failed to fetch AisHub data properly: no data')

    return data[1]


def _extract_infos(message: Dict[str, str]) -> Infos:
    """Extract infos data from a raw message and cast it to output an
    Infos object"""
    if format_ != Format.AIS_ENCODING:
        raise Exception(f"{format_} format not implemented yet,"
                        " please use another format.")

    tmp_dict = {}
    for k, v in message.items():
        if k == 'MMSI':
            tmp_dict['mmsi'] = int(v)
        elif k == 'IMO':
            tmp_dict['imo'] = int(v)
        elif k == 'NAME':
            tmp_dict['name'] = str(v)
        elif k == 'CALLSIGN':
            tmp_dict['callsign'] = str(v)
        elif k == 'TYPE':
            tmp_dict['ship_type'] = int(v)
        elif k == 'A':
            tmp_dict['dim_bow'] = int(v)
        elif k == 'B':
            tmp_dict['dim_stern'] = int(v)
        elif k == 'C':
            tmp_dict['dim_port'] = int(v)
        elif k == 'D':
            tmp_dict['dim_starboard'] = int(v)
        elif k == 'DRAUGHT':
            tmp_dict['draught'] = float(v)/10
        elif k == 'DEST':
            tmp_dict['destination'] = str(v)
        elif k == 'ETA':
            # TODO: understand ETA format
            tmp_dict['eta'] = None

    return Infos(**tmp_dict)


def _extract_position(message: Dict[str, str]) -> Position:
    """Extract position data from a raw message and cast it to output a
    Position object"""
    if format_ != Format.AIS_ENCODING:
        raise Exception(f"{format_} format not implemented yet,"
                        " please use another format.")

    tmp_dict = {}
    lat, lon = 91, 181
    for k, v in message.items():
        if k == 'MMSI':
            tmp_dict['mmsi'] = int(v)
        elif k == 'TIME':
            tmp_dict['time'] = datetime.fromtimestamp(int(v), timezone.utc)
        elif k == 'LATITUDE':
            lat = round(int(v)/600000, 6)
            if lat**2 > 90**2:
                tmp_dict['valid_position'] = False
        elif k == 'LONGITUDE':
            lon = round(int(v)/600000, 6)
            if lon**2 > 180**2:
                tmp_dict['valid_position'] = False
        elif k == 'COG':
            tmp_dict['cog'] = int(v)/10
        elif k == 'SOG':
            tmp_dict['sog'] = int(v)/10
        elif k == 'HEADING':
            tmp_dict['heading'] = int(v)
        elif k == 'PAC':
            tmp_dict['pac'] = bool(v)
        elif k == 'ROT':
            # TODO: Transform that value in a more comprehensive one (deg/min
            # for example)
            tmp_dict['rot'] = int(v)
        elif k == 'NAVSTAT':
            tmp_dict['navstat'] = int(v)

    tmp_dict['point'] = Point(lon, lat)

    return Position(**tmp_dict)


def _extract_infos_position(data: List[Dict[str, str]]
                            ) -> Tuple[Dict[str, Infos], Dict[str, Position]]:
    """Extract Infos and Position from data and put those in a dict indexed by
    mmsi. 
    TODO: use standard dict instead of named tuple"""
    infos_dict, position_dict = {}, {}

    for message in data:
        try:
            mmsi = message['MMSI']
        except KeyError as err:
            logger.error('Error when extracting data: missing MMSI field ? {}',
                         str(err))
            continue

        try:
            infos = _extract_infos(message)
            position = _extract_position(message)
            infos_dict[mmsi] = infos
            position_dict[mmsi] = position
        except TypeError as err:
            logger.error('Error when extracting data: '
                         'missing required fields for Infos or Position ? {}',
                         str(err))

    return (infos_dict, position_dict,)


run = True
should_stop = threading.Condition()


def api_access() -> None:
    """Fetch data from AisHub at regular interval and store it in redis"""
    with should_stop:
        while run:
            try:
                logger.debug("starting api request")
                data = _fetch_last_data()
                logger.debug("data fetched")
            except AisHubError as err:
                logger.error(err)
                data = []

            if data:
                infos_dict, position_dict = _extract_infos_position(data)
                logger.debug("infos and position extracted")

                logger.debug("starting redis update")
                for k, v in infos_dict.items():
                    pipeline_client.set(f'infos:{k}', json.dumps(v._asdict()))
                for k, v in position_dict.items():
                    delta = (v.time-datetime.now(timezone.utc)).total_seconds()
                    expire = POSITION_EXPIRE_TTL - int(delta)
                    pipeline_client.set(
                        f'position:{k}',
                        json.dumps(v._asdict(), default=default_redis_encoder),
                        ex=expire
                    )
                pipeline_client.execute()
                logger.info("redis updated")
                logger.debug("{} unique boats, {} positions",
                             len(redis_client.keys('infos*')),
                             len(redis_client.keys('position*')))

            should_stop.wait(timeout=AISHUBAPI_UPDATE_WINDOW)


service_thread = threading.Thread(target=api_access)


def start() -> None:
    """Start aishubapi service"""
    service_thread.start()


def stop() -> None:
    """Stop aishubapi service"""
    run = False
    with should_stop:
        should_stop.notify_all()
