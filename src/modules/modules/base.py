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