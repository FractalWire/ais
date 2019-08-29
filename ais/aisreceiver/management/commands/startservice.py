from django.core.management.base import BaseCommand
from aisreceiver import service


class Command(BaseCommand):
    help = 'Start aisreceiver service'

    def handle(self, *args, **options):
        service.start()
