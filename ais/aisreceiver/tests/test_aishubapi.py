from __future__ import annotations
import json
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import gzip

from django import test
from django.contrib.gis.geos import Point

from aisreceiver.endpoints import aishubapi
from core.models import BaseMessage


class AishubapiTestCase(test.SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        cls.response = {
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

        class ServeAisData(BaseHTTPRequestHandler):
            """A simple http server use to emulate AisHub api behaviour"""

            def do_GET(self):
                path = self.path.split('?')[0]

                self.send_response(200)
                self.end_headers()
                gzip_bytes = gzip.compress(cls.response[path].encode('utf-8'))
                self.wfile.write(gzip_bytes)

            def log_message(self, format, *args):
                return

        cls.address = 'localhost'
        cls.port = 10201
        cls.httpd = HTTPServer((cls.address, cls.port,), ServeAisData)
        cls.http_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.http_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def setUp(self):
        self.messagesdata = json.loads(self.response['/good'])
        self.firstmessage = self.messagesdata[1][0]
        self.firstmessage_parsed = {
            'mmsi': 232003233,
            'time': datetime(2019, 8, 29, 8, 48, 50, tzinfo=timezone.utc),
            'cog': 0.1,
            'sog': 0.0,
            'heading': 171,
            'rot': 0,
            'navstat': 0,
            'imo': 8914685,
            'name': 'SVITZER MERCIA',
            'callsign': 'MMJY5',
            'ship_type': 52,
            'dim_bow': 20,
            'dim_stern': 12,
            'dim_port': 5,
            'dim_starboard': 5,
            'draught': 5.4,
            'destination': 'LIVERPOOL TUG OPS',
            'eta': None,
            'point': Point(-3.017903, 53.44996),
            'valid_position': True
        }

    def test_fetch_last_data(self):
        """Testing fetching API data from AisHub"""

        base_address = 'http://{0}:{1}'.format(self.address, self.port)

        with self.assertRaises(aishubapi.AisHubError):
            aishubapi.URL = '{0}/{1}'.format(base_address, 'empty')
            fetched_data = aishubapi.fetch_last_data()

        with self.assertRaises(aishubapi.AisHubError):
            aishubapi.URL = '{0}/{1}'.format(base_address, 'bad')
            fetched_data = aishubapi.fetch_last_data()

        aishubapi.URL = '{0}/{1}'.format(base_address, 'good')
        fetched_data = aishubapi.fetch_last_data()
        self.assertEqual(self.messagesdata[1], fetched_data)

    def test_parse_data(self):
        """Testing parsing of the data fetch from AIS Hub API"""

        def assertParse(expected, parsed):
            if expected is None:
                self.assertIsNone(parsed)
                return
            for key in expected:
                self.assertEqual(
                    expected[key],
                    parsed[key],
                    'bad parsing for field {0}'.format(key))
            self.assertEquals(expected, parsed)

        # Bad format test
        with self.assertRaises(Exception):
            aishubapi.format_ = -1
            aishubapi.parse_data(self.firstmessage)

        # Regular test
        self.setUp()
        aishubapi.format_ = aishubapi.Format.AIS_ENCODING
        parsed_result = aishubapi.parse_data(self.firstmessage)
        assertParse(self.firstmessage_parsed, parsed_result)

        # Missing required fields test
        # ['MMSI', 'TIME']
        for f in [f.upper() for f in BaseMessage._aismeta.required_fields]:
            self.setUp()
            del self.firstmessage[f]
            self.firstmessage_parsed = None
            parsed_result = aishubapi.parse_data(self.firstmessage)
            assertParse(self.firstmessage_parsed, parsed_result)

        # bad latitude test
        self.setUp()
        self.firstmessage['LATITUDE'] = 91*600000
        self.firstmessage_parsed['point'] = None
        self.firstmessage_parsed['valid_position'] = False
        parsed_result = aishubapi.parse_data(self.firstmessage)
        assertParse(self.firstmessage_parsed, parsed_result)

        # bad longitude test
        self.setUp()
        self.firstmessage['LONGITUDE'] = 181*600000
        self.firstmessage_parsed['point'] = None
        self.firstmessage_parsed['valid_position'] = False
        parsed_result = aishubapi.parse_data(self.firstmessage)
        assertParse(self.firstmessage_parsed, parsed_result)

        # Missing str fields test
        # ['NAME', 'CALLSIGN', 'DESTINATION']
        str_fields_mapping = dict(name="NAME",
                                  callsign="CALLSIGN",
                                  destination="DEST")
        for f in BaseMessage._aismeta.not_null_str_fields:
            if f not in str_fields_mapping:
                raise KeyError("mapping missing a field: {}".format(f))
            self.setUp()
            del self.firstmessage[str_fields_mapping[f]]
            self.firstmessage_parsed[f.lower()] = ''
            parsed_result = aishubapi.parse_data(self.firstmessage)
            assertParse(self.firstmessage_parsed, parsed_result)

    def test_extract_messages(self):
        """Testing parsing of multiple messages from AIS Hub API"""
        # Test for good number of message
        extracted_messages = aishubapi.extract_messages(self.messagesdata[1])
        self.assertEqual(len(extracted_messages), 2)

        # Test for good number of message with a bad message in it
        self.setUp()
        del self.messagesdata[1][1]['MMSI']
        extracted_messages = aishubapi.extract_messages(self.messagesdata[1])
        self.assertEqual(len(extracted_messages), 1)
