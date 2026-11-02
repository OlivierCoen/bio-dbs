from django.test import TestCase
from databases.models import Database
from typing import ClassVar
from inspect import isabstract
from abc import ABCMeta
from pathlib import Path
from tempfile import gettempdir


class DatabaseTest(TestCase, metaclass=ABCMeta):

    NAME: ClassVar[str]

    db: Database

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # in case the subclass is not abtract
        # checking if mandatory class attribute is defined
        if not isabstract(cls) and not hasattr(cls, "NAME"):
                raise TypeError(f"{cls.__name__} must define 'NAME' class attributes")

    def setUp(self):
        self.db = Database.objects.create(
            name=self.NAME, display_name=self.NAME.capitalize(), enabled=True
        )

    def tearDown(self):
        self.db.delete()

    def get_dest_path(self):
        return Path(gettempdir()) / self.NAME
