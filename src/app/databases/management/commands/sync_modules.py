from django.core.management.base import BaseCommand
from modules.registry import discover_modules
from databases.models import Database

class Command(BaseCommand):
    def handle(self, *args, **options):
        for cls in discover_modules():
            db, created = Database.objects.update_or_create(name=cls.get_name())
            db.display_name = cls.get_display_name()
            db.module = cls
            status = 'created' if created else 'updated'
            self.stdout.write(f"{status.capitalize()}: {db}")