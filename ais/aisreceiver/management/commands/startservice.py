from django.core.management.base import BaseCommand
from core.service import start


class Command(BaseCommand):
    help = 'Start aisreceiver service'

    def handle(self, *args, **options):
        start()
