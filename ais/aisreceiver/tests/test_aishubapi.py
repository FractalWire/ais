from __future__ import annotations
import json
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import gzip
import unittest
from django import test
from django.contrib.gis.geos import Point

from aisreceiver.endpoints import aishubapi
from aisreceiver.aismessage import Infos, Position


class ExtractDataTestCase(test.SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        rawmessages = '[{"MMSI": "244070156", "TIME": "1302514295", "LONGITUDE": "2912427", "LATITUDE": "31091961", "COG": "1513", "SOG": "40", "HEADING": "511", "NAVSTAT": "0", "PAC": "0", "ROT": "-128", "IMO": "0", "NAME": "RPA03", "CALLSIGN": "PD5102", "TYPE": "55", "DEVICE": "1", "A": "8", "B": "10", "C": "3", "D": "2", "DRAUGHT": "15", "DEST": "PATROL", "ETA": "1596", "AISVER": "0"}, {"MMSI": "246538000", "TIME": "1302514282", "LONGITUDE": "2752877", "LATITUDE": "31476019", "COG": "2632", "SOG": "0", "HEADING": "511", "NAVSTAT": "0", "PAC": "0", "ROT": "-128", "IMO": "7700180", "NAME": "SIRIUS", "CALLSIGN": "PBRW", "TYPE": "52", "DEVICE": "1", "A": "6", "B": "20", "C": "3", "D": "5", "DRAUGHT": "48", "DEST": "IJMUIDEN", "ETA": "849920", "AISVER": "0"}]'
        cls.messagesdata = json.loads(rawmessages)
        cls.firstmessage = cls.messagesdata[0]

        class ServeAisData(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                gzip_bytes = gzip.compress(rawmessages.encode('utf-8'))
                self.wfile.write(gzip_bytes)

        cls.address = 'localhost'
        cls.port = 10201
        cls.httpd = HTTPServer((cls.address, cls.port,), ServeAisData)
        cls.http_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.http_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_extract_infos(self):
        infos: Infos = Infos(
            mmsi='244070156',
            imo='0',
            callsign='',
            name='RPA03',
            ship_type=55,
            dim_bow=8,
            dim_stern=10,
            dim_port=3,
            dim_starboard=2,
            eta=None,
            draught=1.5,
            destination='PATROL'
        )

        extracted_infos: Infos = aishubapi._extract_infos(self.firstmessage)

        self.assertEqual(infos, extracted_infos)
        self.assertEqual(infos.mmsi, extracted_infos.mmsi)
        self.assertEqual(infos.imo, extracted_infos.imo)
        self.assertEqual(infos.callsign, extracted_infos.callsign)
        self.assertEqual(infos.name, extracted_infos.name)
        self.assertEqual(infos.ship_type, extracted_infos.ship_type)
        self.assertEqual(infos.dim_bow, extracted_infos.dim_bow)
        self.assertEqual(infos.dim_stern, extracted_infos.dim_stern)
        self.assertEqual(infos.dim_port, extracted_infos.dim_port)
        self.assertEqual(infos.dim_starboard, extracted_infos.dim_starboard)
        self.assertIsNone(infos.eta, extracted_infos.eta)
        self.assertEqual(infos.draught, extracted_infos.draught)
        self.assertEqual(infos.destination, extracted_infos.destination)

    def test_extract_position(self):
        position: Position = Position(
            mmsi='244070156',
            time=datetime(2011, 4, 11, 9, 31, 35, tzinfo=timezone.utc),
            point=Point(4.854045, 51.819935),
            cog=151.3,
            sog=4.0,
            heading=511,
            pac=True,
            rot=-128,
            navstat=0
        )

        extracted_position: Position = aishubapi._extract_position(
            self.firstmessage)

        self.assertEqual(position, extracted_position)
        self.assertEqual(position.mmsi, extracted_position.mmsi)
        self.assertEqual(position.time, extracted_position.time)
        self.assertEqual(position.point, extracted_position.point)
        self.assertEqual(position.cog, extracted_position.cog)
        self.assertEqual(position.sog, extracted_position.sog)
        self.assertEqual(position.heading, extracted_position.heading)
        self.assertEqual(position.pac, extracted_position.pac)
        self.assertEqual(position.rot, extracted_position.rot)
        self.assertEqual(position.navstat, extracted_position.navstat)

    @unittest.skip
    def test_extract_infos_position(self):
        infos_dict, position_dict = aishubapi._extract_infos_position(
            self.messagesdata)
        # print(position_dict['244070156'].point)

    def test_fetch_last_data(self):
        aishubapi.URL = 'http://{0}:{1}'.format(self.address, self.port)
        fetched_data = aishubapi._fetch_last_data()
        self.assertEqual(self.messagesdata, fetched_data)
