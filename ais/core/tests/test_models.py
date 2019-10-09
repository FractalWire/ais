import random
from datetime import datetime, timedelta

from django import test
from django.contrib.gis.geos import Point

from core.models import AisData, BaseInfos, Message, ShipInfos, _copy_data


class CopyCsvTestCase(test.TestCase):
    def random_AisData(self, mmsi, time) -> AisData:
        """Quick and dirty random factory"""
        bm = BaseInfos(
            mmsi=mmsi,
            time=time,
            point=Point(random.randrange(0, 100), random.randrange(0, 90)),
            valid_position=True,
            cog=random.random()*360,
            sog=random.random()*360,
            heading=int(random.random()*360),
            pac=False,
            rot=int(random.random()*360),
            navstat=int(random.random()*360),
            imo=int(random.random()*360),
            callsign='',
            name='',
            ship_type=int(random.random()*360),
            dim_bow=int(random.random()*360),
            dim_stern=int(random.random()*360),
            dim_port=int(random.random()*360),
            dim_starboard=int(random.random()*360),
            eta=None,
            draught=random.random()*360,
            destination=''
        ).__dict__
        del bm['_state']
        return bm

    def setUp(self):
        rnd_mmsi_cnt = 1000
        self.mmsi_set = set(random.randrange(10**6, 10**7)
                            for _ in range(rnd_mmsi_cnt))
        # self.data_cnt = 10000
        self.time = datetime.now()
        # data with unique mmsi per row
        self.data = [self.random_AisData(mmsi, self.time)
                     for mmsi in random.sample(self.mmsi_set, len(self.mmsi_set))]
        Message.objects.all().delete()
        ShipInfos.objects.all().delete()
        _copy_data(self.data)

    # def tearDown(self):
        # self.f.close()

    def test_copy_csv(self):
        # TODO: separate into different test maybe...

        # Test that we have same number of data in input and in the database
        msg_cnt = Message.objects.count()
        shipinfos_cnt = ShipInfos.objects.count()
        self.assertEqual(msg_cnt, len(self.data))
        self.assertEqual(shipinfos_cnt, len(self.data))

        # Test that same new rows are rejected
        self.setUp()
        old_msg_cnt = Message.objects.count()
        new_data = self.data[:200]
        _copy_data(new_data)
        msg_cnt = Message.objects.count()
        self.assertEqual(msg_cnt, old_msg_cnt)

        # Test that older new rows are rejected by ShipInfos
        self.setUp()
        old_shipinfos_cnt = ShipInfos.objects.count()
        new_data_cnt = 200
        new_data = self.data[:new_data_cnt]
        for d in new_data:
            d['time'] = d['time']-timedelta(1)
        _copy_data(new_data)
        shipinfos_cnt = ShipInfos.objects.count()
        self.assertEqual(shipinfos_cnt, old_shipinfos_cnt)

        # Test that newer recent rows are accepted by Message
        self.setUp()
        old_msg_cnt = Message.objects.count()
        new_data_cnt = 200
        new_data = self.data[:new_data_cnt]
        for d in new_data:
            d['time'] = d['time']+timedelta(1)
        _copy_data(new_data)
        msg_cnt = Message.objects.count()
        self.assertEqual(msg_cnt, old_msg_cnt+new_data_cnt)

        # Test that newer rows in Message are in ShipInfos
        self.setUp()
        new_data_cnt = 200
        new_data = self.data[:new_data_cnt]
        for d in new_data:
            d['time'] = d['time']+timedelta(1)
        _copy_data(new_data)
        recent_message = (Message.objects.order_by('mmsi', '-time').
                          distinct('mmsi'))
        all_times = recent_message.values('time', 'mmsi__time')

        self.assertEqual(shipinfos_cnt, old_shipinfos_cnt)
        self.assertTrue(
            all([times['time'] == times['mmsi__time'] for times in all_times])
        )
