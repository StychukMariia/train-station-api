import time
from django.core.management.base import BaseCommand
from django.db import OperationalError
from psycopg import OperationalError as PsycopgOpError


class Command(BaseCommand):
    """Django command to wait for database to be available."""

    def handle(self, *options, **kwargs):
        self.stdout.write("Waiting for database...")
        db_up = False
        while not db_up:
            try:
                self.check(databases=["default"])
                db_up = True
            except (OperationalError, PsycopgOpError):
                self.stdout.write("Database unavailable, waiting 1 second...")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Database available!"))
