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
        response = {
            '/empty': '[]',
            '/bad': '''[
    {
        "ERROR": true,
        "USERNAME": "username",
        "FORMAT": "AIS",
        "RECORDS": 2,
        "ERROR_MESSAGE": "Some error message"
    }]
''',
            '/good': '''[
    {
        "ERROR": false,
        "USERNAME": "username",
        "FORMAT": "AIS",
        "RECORDS": 2
    },
    [
        {
            "MMSI": 232003233,
            "TIME": "1567068530",
            "LONGITUDE": -1810742,
            "LATITUDE": 32069976,
            "COG": 1,
            "SOG": 0,
            "HEADING": 171,
            "ROT": 0,
            "NAVSTAT": 0,
            "IMO": 8914685,
            "NAME": "SVITZER MERCIA",
            "CALLSIGN": "MMJY5",
            "TYPE": 52,
            "A": 20,
            "B": 12,
            "C": 5,
            "D": 5,
            "DRAUGHT": 54,
            "DEST": "LIVERPOOL TUG OPS",
            "ETA": 582144
        },
        {
            "MMSI": 257173700,
            "TIME": "1567068508",
            "LONGITUDE": 6284011,
            "LATITUDE": 35548940,
            "COG": 3301,
            "SOG": 0,
            "HEADING": 13,
            "ROT": 0,
            "NAVSTAT": 5,
            "IMO": 0,
            "NAME": "TUROY",
            "CALLSIGN": "LJMV",
            "TYPE": 69,
            "A": 7,
            "B": 7,
            "C": 2,
            "D": 3,
            "DRAUGHT": 0,
            "DEST": "",
            "ETA": 67649
        }
    ]]
''',
        }
        cls.messagesdata = json.loads(response['/good'])
        cls.firstmessage = cls.messagesdata[1][0]

        class ServeAisData(BaseHTTPRequestHandler):
            def do_GET(self):
                path = self.path.split('?')[0]

                self.send_response(200)
                self.end_headers()
                gzip_bytes = gzip.compress(response[path].encode('utf-8'))
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
            mmsi=232003233,
            imo=8914685,
            callsign='MMJY5',
            name='SVITZER MERCIA',
            ship_type=52,
            dim_bow=20,
            dim_stern=12,
            dim_port=5,
            dim_starboard=5,
            eta=None,
            draught=5.4,
            destination='LIVERPOOL TUG OPS'
        )

        extracted_infos: Infos = aishubapi._extract_infos(self.firstmessage)

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

        self.assertEqual(infos, extracted_infos)

    def test_extract_position(self):
        position: Position = Position(
            mmsi=232003233,
            time=datetime(2019, 8, 29, 8, 48, 50, tzinfo=timezone.utc),
            point=Point(-3.017903, 53.44996),
            cog=0.1,
            sog=0,
            heading=171,
            pac=False,
            rot=0,
            navstat=0
        )

        extracted_position: Position = aishubapi._extract_position(
            self.firstmessage)

        self.assertEqual(position.mmsi, extracted_position.mmsi)
        self.assertEqual(position.time, extracted_position.time)
        self.assertEqual(position.point, extracted_position.point)
        self.assertEqual(position.cog, extracted_position.cog)
        self.assertEqual(position.sog, extracted_position.sog)
        self.assertEqual(position.heading, extracted_position.heading)
        self.assertEqual(position.pac, extracted_position.pac)
        self.assertEqual(position.rot, extracted_position.rot)
        self.assertEqual(position.navstat, extracted_position.navstat)

        self.assertEqual(position, extracted_position)

    @unittest.skip
    def test_extract_infos_position(self):
        infos_dict, position_dict = aishubapi._extract_infos_position(
            self.messagesdata)
        # print(position_dict['244070156'].point)

    def test_fetch_last_data(self):

        base_address = 'http://{0}:{1}'.format(self.address, self.port)

        with self.assertRaises(aishubapi.AisHubError):
            aishubapi.URL = '{0}/{1}'.format(base_address, 'empty')
            fetched_data = aishubapi._fetch_last_data()

        with self.assertRaises(aishubapi.AisHubError):
            aishubapi.URL = '{0}/{1}'.format(base_address, 'bad')
            fetched_data = aishubapi._fetch_last_data()

        aishubapi.URL = '{0}/{1}'.format(base_address, 'good')
        fetched_data = aishubapi._fetch_last_data()
        self.assertEqual(self.messagesdata[1], fetched_data)
