"""This module manages the interaction with AISHub API
https://www.aishub.net/api"""
from __future__ import annotations
from typing import List, Dict, Any
import requests
import gzip
import json
import threading
from io import BytesIO
from enum import Flag, IntFlag
from datetime import datetime, timezone

from django.contrib.gis.geos import Point

from core.models import BaseInfos

from aisreceiver.app_settings import AISHUBAPI_WINDOW
from aisreceiver import aisbuffer

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


def fetch_last_data() -> List[Dict[str, Any]]:
    """Fetch last data via AisHubAPI"""
    data: List[Any] = []
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


def parse_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse incoming data to match message format"""

    if format_ != Format.AIS_ENCODING:
        raise Exception(f"{format_} format not implemented yet,"
                        " please use another format.")
    message: Dict[str, Any] = {}
    lat, lon = 91.0, 181.0
    for k, v in data.items():
        if k == 'MMSI':
            message['mmsi'] = int(v)
        elif k == 'TIME':
            message['time'] = datetime.fromtimestamp(int(v), timezone.utc)
        elif k == 'LATITUDE':
            lat = round(int(v)/600000, 6)
        elif k == 'LONGITUDE':
            lon = round(int(v)/600000, 6)
        elif k == 'COG':
            message['cog'] = int(v)/10
        elif k == 'SOG':
            message['sog'] = int(v)/10
        elif k == 'HEADING':
            message['heading'] = int(v)
        elif k == 'PAC':
            message['pac'] = bool(v)
        elif k == 'ROT':
            # TODO: Transform that value in a more comprehensive one (deg/min
            # for example)
            message['rot'] = int(v)
        elif k == 'NAVSTAT':
            message['navstat'] = int(v)

        elif k == 'IMO':
            message['imo'] = int(v)
        elif k == 'NAME':
            message['name'] = str(v)
        elif k == 'CALLSIGN':
            message['callsign'] = str(v)
        elif k == 'TYPE':
            message['ship_type'] = int(v)
        elif k == 'A':
            message['dim_bow'] = int(v)
        elif k == 'B':
            message['dim_stern'] = int(v)
        elif k == 'C':
            message['dim_port'] = int(v)
        elif k == 'D':
            message['dim_starboard'] = int(v)
        elif k == 'DRAUGHT':
            message['draught'] = float(v)/10
        elif k == 'DEST':
            message['destination'] = str(v)
        elif k == 'ETA':
            # TODO: understand ETA format
            message['eta'] = None

    required_fields = BaseInfos._aismeta.required_fields
    if not all(f in message for f in required_fields):
        logger.error('Error when parsing data: missing required fields: {}',
                     [f for f in message if f in required_fields])
        return None

    for k in BaseInfos._aismeta.not_null_str_fields:
        if k in message and message[k] is not None:
            continue
        message[k] = ''

    message['valid_position'] = True
    if lat**2 > 90**2:
        message['valid_position'] = False
    if lon**2 > 180**2:
        message['valid_position'] = False

    if not message['valid_position']:
        message['point'] = None
    else:
        message['point'] = Point(lon, lat)

    return message


def extract_messages(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract raw messages from data and put those in a list"""

    message_list = []
    for d in data:
        message = parse_data(d)

        if message:
            message_list.append(message)

    return message_list


run = True
should_stop = threading.Condition()


def api_access() -> None:
    """Fetch data from AisHub at regular interval and store it in a buffer"""

    with should_stop:
        data = []
        while run:
            logger.debug('')
            logger.debug("starting api request")
            try:
                data = fetch_last_data()
                logger.debug("data fetched from AisHub")
            except AisHubError as err:
                logger.error('{}', err)

            if data:
                messages = extract_messages(data)
                logger.debug("messages extracted")
                logger.debug("starting buffer update")
                aisbuffer.messages.update(messages)
                # aisbuffer.last_messages.update(messages)
                with aisbuffer.messages.lock:
                    logger.info("{} aismessages waiting for postgres",
                                len(aisbuffer.messages.data))
                logger.info("buffer updated")

                # cleanup, we're in a loop
                messages.clear()
                data.clear()

            should_stop.wait(timeout=AISHUBAPI_WINDOW)


service_thread = threading.Thread(target=api_access)


def start() -> None:
    """Start aishubapi service"""
    service_thread.start()


def stop() -> None:
    """Stop aishubapi service"""
    # run = False
    with should_stop:
        should_stop.notify_all()
