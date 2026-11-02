from django.core.management.base import BaseCommand
from modules.registry import discover_modules
from databases.models import Database
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        discovered_modules = discover_modules().values()
        logger.info(f"Discovered modules: {', '.join([cls.DISPLAY_NAME for cls in discovered_modules])}")
        for cls in discovered_modules:
            db, created = Database.objects.update_or_create(
                name=cls.NAME,
                display_name=cls.DISPLAY_NAME,
            )
            status = 'created' if created else 'updated'
            logger.info(f"{status.capitalize()}: {db}")
            