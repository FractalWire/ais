from datetime import datetime, timezone
import unittest
from django import test
from django.contrib.gis.geos import Point

from core.serializers.json import redis_object_hook, default_redis_encoder


class JsonSerializerTestCase(test.SimpleTestCase):
    def setUp(self):
        self.timestamp = 100000
        self.coords = (10.5, -10.5)

    def test_default_redis_encoder(self) -> None:
        d = datetime.fromtimestamp(self.timestamp, tz=timezone.utc)
        expected_time_obj = dict(__datetime__=True, utctimestamp=self.timestamp)

        p = Point(*self.coords)
        expected_point_obj = dict(__point__=True, coords=self.coords)

        class NotSerializable:
            pass

        self.assertEqual(default_redis_encoder(d), expected_time_obj)
        self.assertEqual(default_redis_encoder(p), expected_point_obj)

        with self.assertRaises(TypeError):
            default_redis_encoder(NotSerializable())

    def test_redis_object_hook(self) -> None:
        time_obj = dict(__datetime__=True, utctimestamp=self.timestamp)
        expected_datetime = datetime.fromtimestamp(
            self.timestamp, tz=timezone.utc)

        point_obj = dict(__point__=True, coords=self.coords)
        expected_point = Point(*self.coords)

        another_obj = dict(another="obj")

        self.assertEqual(redis_object_hook(time_obj), expected_datetime)
        self.assertEqual(redis_object_hook(point_obj), expected_point)
        self.assertEqual(redis_object_hook(another_obj), another_obj)
