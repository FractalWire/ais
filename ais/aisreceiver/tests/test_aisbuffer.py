from __future__ import annotations
import io

from django import test

from aisreceiver.aisbuffer import AisBuffer
# from core.models import AisData


class AisBufferTestCase(test.SimpleTestCase):

    def setUp(self):
        self.aisbuffer = AisBuffer()

        self.dummy_data = [
            {"mmsi": 1234, "name": "dummyname1"},
            {"mmsi": 4567, "name": "dummyname2"},
            {"mmsi": 8901, "name": "dummyname3"},
        ]
        self.keyset = {d['mmsi'] for d in self.dummy_data}

        self.aisbuffer.update(self.dummy_data)

    def test_update(self):

        # Test if all keys from dummy_data are in the buffer
        self.assertEqual(self.keyset, self.aisbuffer.data.keys())

        # Test if a data with the same key is rejected
        self.setUp()
        new_mmsi = list(self.keyset)[0]
        new_data = [{"mmsi": new_mmsi, "name": "somethingelse"}]
        old_value = {**self.aisbuffer.data[new_mmsi]}
        self.aisbuffer.update(new_data)
        self.assertNotEqual(self.aisbuffer.data[new_mmsi], new_data[0])
        self.assertEqual(self.aisbuffer.data[new_mmsi], old_value)

        # Test if new data is correctly added
        self.setUp()
        new_mmsi = 1000
        new_data = [{"mmsi": new_mmsi, "name": "somethingelse"}]
        old_len = len(self.aisbuffer.data)
        old_keys = set(self.aisbuffer.data.keys())
        self.aisbuffer.update(new_data)
        self.assertEqual(len(self.aisbuffer.data), old_len+len(new_data))
        self.assertEqual(self.aisbuffer.data.keys(), old_keys.union({new_mmsi}))

    def test_generator(self):
        batch_size = 2
        old_total_data = len(self.aisbuffer.data)
        total_data = 0

        for data in self.aisbuffer.generator(batch_size):
            # Test if the good amount of data is passed
            self.assertTrue(len(data) <= batch_size)
            total_data += len(data)

        # Test if all the data have been passed
        self.assertEqual(old_total_data, total_data)
        # Test if there is no remaining data
        self.assertEqual(len(self.aisbuffer.data), 0)

    def test_prepare_csv(self):
        # Test if all data is written to file
        old_len = len(self.aisbuffer.data)
        f = io.StringIO()
        self.aisbuffer.prepare_csv(f)
        f.seek(0)
        lines = f.readlines()
        f.close()

        self.assertEqual(old_len, len(lines))

        # Test if csv escape properly
        # sep = '|'
        # escapechar = '\\'
        # quotechar = ''
        # sql_quotechar = '"'
        # sql_null = ''

        self.aisbuffer.data.clear()
        new_mmsi = 1000
        new_data = [{"mmsi": new_mmsi,
                     "name": "This '' ' need to be escaped | \\ somehow\" \\"}]
        self.aisbuffer.update(new_data)

        f = io.StringIO()
        self.aisbuffer.prepare_csv(f)
        f.seek(0)
        line = f.readline()
        field = '|'.join(line.split('|')[12:14])
        f.close()

        # NOTE: " character should not be escaped here, this is the
        # responsability of deserializer to replace " character somehow.
        # Mandatory due to the weirdness of None and empty string treatement by
        # csv module...
        expected_field = "This '' ' need to be escaped \\| \\\\ somehow\" \\\\"
        self.assertEqual(field, expected_field)
