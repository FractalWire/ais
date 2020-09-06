from django.core.management.base import BaseCommand
from aisreceiver.service import AisService
# from geoserver.service import GeoserverService
import signal


class Command(BaseCommand):
    help = 'Start all ais services'

    def handle(self, *args, **options):
        ais_service = AisService()
        # geoserver_service = GeoserverService([ais_service])

        def stop_services(sig_name, stack) -> None:
            ais_service.stop()
            # geoserver_service.stop()
        # To handle graceful exit
        signal.signal(signal.SIGINT, stop_services)
        signal.signal(signal.SIGTERM, stop_services)

        ais_service.start()
        # geoserver_service.start()

        ais_service.thread.join()
        # geoserver_service.thread.join()
