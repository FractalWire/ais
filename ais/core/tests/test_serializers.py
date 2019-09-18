from datetime import datetime, timezone
from django import test
from django.contrib.gis.geos import Point

from core.serializers.json import object_decoder, default_encoder


class JsonSerializerTestCase(test.SimpleTestCase):
    def setUp(self):
        self.timestamp = 100000
        self.coords = (10.5, -10.5)

    def test_default_encoder(self) -> None:
        d = datetime.fromtimestamp(self.timestamp, tz=timezone.utc)
        expected_time_obj = dict(__datetime__=True, utctimestamp=self.timestamp)

        p = Point(*self.coords)
        expected_point_obj = dict(__point__=True, coords=self.coords)

        class NotSerializable:
            pass

        self.assertEqual(default_encoder(d), expected_time_obj)
        self.assertEqual(default_encoder(p), expected_point_obj)

        with self.assertRaises(TypeError):
            default_encoder(NotSerializable())

    def test_object_decoder(self) -> None:
        time_obj = dict(__datetime__=True, utctimestamp=self.timestamp)
        expected_datetime = datetime.fromtimestamp(
            self.timestamp, tz=timezone.utc)

        point_obj = dict(__point__=True, coords=self.coords)
        expected_point = Point(*self.coords)

        another_obj = dict(another="obj")

        self.assertEqual(object_decoder(time_obj), expected_datetime)
        self.assertEqual(object_decoder(point_obj), expected_point)
        self.assertEqual(object_decoder(another_obj), another_obj)
