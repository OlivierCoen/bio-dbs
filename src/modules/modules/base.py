from abc import ABC
from pathlib import Path
from typing import ClassVar

class Module(ABC):

    NAME: ClassVar[str]
    DISPLAY_NAME: ClassVar[str]

    @classmethod
    def check_updates(cls) -> str:
        """
        Returns the latest available version of the db.
        """
        raise NotImplementedError()

    @classmethod
    def update(cls, dest_dir: Path, version: str) -> Path:
        """
        Downloads the specified version of the db to the specified location.
        Returns the path to the db.
        """
        raise NotImplementedError()

    @classmethod
    def get_name(cls):
        if getattr(cls, 'NAME', None) is None:
            raise NotImplementedError(f"'NAME' class attribute was not set for {cls.__name__}")
        return cls.NAME

    @classmethod
    def get_display_name(cls):
        if getattr(cls, 'DISPLAY_NAME', None) is None:
            raise NotImplementedError(f"'DISPLAY_NAME' class attribute was not set for {cls.__name__}")
        return cls.DISPLAY_NAME