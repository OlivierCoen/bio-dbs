from inspect import isabstract
from abc import ABC, abstractmethod
from typing import ClassVar
from pathlib import Path
import subprocess
import logging
import os
import hashlib

logger = logging.getLogger(__name__)


class BaseModule(ABC):

    DEFAULT_NCPUS: ClassVar[str] = "8"

    NAME: ClassVar[str]
    DISPLAY_NAME: ClassVar[str]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # in case the subclass is not abtract
        # checking if mandatory class attributes were defined
        if not isabstract(cls):
            missing = [a for a in ("NAME", "DISPLAY_NAME") if not hasattr(cls, a)]
            if missing:
                raise TypeError(
                    f"{cls.__name__} must define class attributes: {', '.join(missing)}"
                )

    @classmethod
    @abstractmethod
    def check_updates(cls) -> dict:
        """
        Check updates and returns metadata of the latest available version of the db.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def update(cls, dest_dir: str, version: str, subdb_names: list[str]) -> None:
        """
        Downloads the specified version of the db to the specified location.
        Returns the path to the db.
        """
        raise NotImplementedError


    @classmethod
    def get_ncpus(cls, supplied_ncpus: int | None = None) -> int:
        if supplied_ncpus is not None:
            return supplied_ncpus
        ncpus: str = os.getenv("NCPUS", cls.DEFAULT_NCPUS)
        try:
            return int(ncpus)
        except ValueError:
            raise TypeError(f"Could not convert number of CPUs {ncpus} to Integer")


    @classmethod
    def download_file(cls, url: str, dest_dir: str, ncpus: int | None = None) -> Path:
        ncpus = cls.get_ncpus(ncpus)
        filename = url.split('/')[-1]
        logger.info(f"Downloading {url} to {dest_dir}")
        cmd = [
            'aria2c', 
            '-s', str(ncpus), 
            '-x', str(ncpus),  
            '--optimize-concurrent-downloads', 
            '--check-integrity=true', 
            '--dir', 
            dest_dir, 
            url
        ]
        subprocess.run(cmd, check=True)
        dest_file = Path(dest_dir) / filename
        logger.info(f"{filename} successfully downloaded to {dest_file}")
        return dest_file


    @classmethod
    def download_md5_and_checksum(cls, md5_url: str, dest_dir: str) -> None:
        md5_file = cls.download_file(md5_url, dest_dir, ncpus=1)
        checksum_directory(md5_file, dest_dir)



class WrongChecksumError(Exception):
    pass


def checksum_directory(md5_file: Path, dest_dir: str) -> None:
    with open(md5_file, 'r') as fin:
        lines = [line.strip() for line in fin]
    for line in lines:
        if not line:
            continue
        digest, filename = line.split(maxsplit=1) 
        filename = filename.lstrip("*")              # strip binary-mode marker if present
        actual = md5sum(Path(dest_dir) / filename)
        if actual != digest:
            raise WrongChecksumError(f"Obtained wrong md5sum for file {filename}")
    logger.info("MD5 checksum successful")


def md5sum(path: Path, chunk_size: int = 2**20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()
        