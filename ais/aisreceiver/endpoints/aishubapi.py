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

from aisreceiver.aismessage import Infos, Position, infos_keys, position_keys
from aisreceiver.buffer import buffer_lock, infos_buffer, position_buffer


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


# TODO: Put that in a config file maybe
# minimum value: 1 minute. AisHub does not allowed more frequent update
_POSITIONS_UPDATE_WINDOW = 5 * 60  # in seconds

URL = 'http://data.aishub.net/ws.php?'

format_ = Format.AIS_ENCODING
output = Output.JSON
compression = Compression.GZIP

parameters = {
    'username': '',
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
    data = {}
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
        # TODO: log error
        print('Error when trying to retrieve AisHub last data:', err,
              file=sys.stderr)

    return data


def _extract_infos(message: Dict[str, str]) -> Infos:
    """Extract infos data from a raw message and cast it to output an
    Infos object"""
    if format_ != Format.AIS_ENCODING:
        raise Exception(f"{format_} format not implemented yet,"
                        " please use another format.")

    tmp_dict = {}
    for k, v in message.items():
        if k == 'MMSI':
            tmp_dict['mmsi'] = v
        elif k == 'IMO':
            tmp_dict['imo'] = v
        elif k == 'NAME':
            tmp_dict['name'] = v
        elif k == 'DEST':
            tmp_dict['destination'] = v
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
            tmp_dict['mmsi'] = v
        elif k == 'TIME':
            tmp_dict['time'] = datetime.fromtimestamp(int(v), timezone.utc)
        elif k == 'LATITUDE':
            lat = int(v)/600000
            if lat**2 > 90**2:
                tmp_dict['valid_position'] = False
        elif k == 'LONGITUDE':
            lon = int(v)/600000
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
    mmsi. This make it ready to consume for the buffer dictionaries"""
    infos_dict, position_dict = {}, {}

    for message in data:
        try:
            mmsi = message['MMSI']
            infos = _extract_infos(message)
            position = _extract_position(message)
            infos_dict[mmsi] = infos
            position_dict[mmsi] = position
        except KeyError as err:
            # TODO: log error
            print('Error when extracting data: missing MMSI field ?', str(err),
                  file=sys.stderr)
        except TypeError as err:
            # TODO: log error
            print('Error when extracting data: '
                  'missing required fields for Infos or Position ?', str(err),
                  file=sys.stderr)

    return (infos_dict, position_dict,)


run = True
should_stop = threading.Condition()


def api_access() -> None:
    """Fetch data from AisHub at regular interval and store it in the buffers"""
    with should_stop:
        while run:
            data = _fetch_last_data()
            infos_dict, position_dict = _extract_infos_position(data)

            with buffer_lock:
                infos_buffer.update(infos_dict)
                position_buffer.update(position_dict)

            should_stop.wait(timeout=_POSITIONS_UPDATE_WINDOW)


service_thread = threading.Thread(target=api_access)


def start() -> None:
    """Start aishubapi service"""
    service_thread.start()


def stop() -> None:
    """Stop aishubapiservice"""
    run = False
    with should_stop:
        should_stop.notify_all()
