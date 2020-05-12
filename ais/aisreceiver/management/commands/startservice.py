from django.core.management.base import BaseCommand
from aisreceiver.service import AisService
import signal


class Command(BaseCommand):
    help = 'Start aisreceiver service'

    def handle(self, *args, **options):
        ais_service = AisService()

        # To handle graceful exit
        signal.signal(signal.SIGINT, lambda a, b: ais_service.stop())
        signal.signal(signal.SIGTERM, lambda a, b: ais_service.stop())

        ais_service.start()
        ais_service.thread.join()
