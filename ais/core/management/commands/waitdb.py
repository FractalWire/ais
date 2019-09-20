import time

from django.db import connections
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Command to wait until database is up"""

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database to start.', ending='')
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections['default']
            except OperationalError:
                self.stdout.write('.', ending='')
                time.sleep(1)
        self.stdout.write('')
        self.stdout.write('The database is online.')
