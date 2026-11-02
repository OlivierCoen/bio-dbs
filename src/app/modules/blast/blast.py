from ..base import BaseModule
from typing import ClassVar
from statistics import mean

import httpx
from datetime import datetime
import logging


from tenacity import (
    before_sleep_log,
    retry,
    stop_after_delay,
    wait_exponential,
    retry_if_exception
)
from bs4 import BeautifulSoup


REQUEST_TIMEOUT = 600

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.ERROR)


class Blast(BaseModule):

    NAME: ClassVar[str] = "blast"
    DISPLAY_NAME: ClassVar[str] = "Blast"

    BLAST_DB_FTP_BASE_URL: ClassVar[str] = "https://ftp.ncbi.nlm.nih.gov/blast/db/"
    BLAST_DATETIME_FORMAT: ClassVar[str] = '%Y-%m-%d %H:%M'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # MANDATORY METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def check_updates(cls) -> dict:
        """
        Returns the latest available version of the db.
        """
        blast_db_metadata = cls.get_blast_db_metadata()
        return cls.get_aggregated_metadata(blast_db_metadata)


    @classmethod
    def update(cls, dest_dir: str, version: str, subdb_names: list[str]) -> None:
        """
        Returns the latest available version of the db.
        """
        logger.info(f"Downloading {', '.join(subdb_names)}")
        blast_db_metadata = cls.get_blast_db_metadata()
        cls.download(blast_db_metadata, dest_dir, subdb_names)


    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HELPER METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def get_blast_db_metadata(cls):
        soup = parse_page_data(cls.BLAST_DB_FTP_BASE_URL)
        
        # adding progress bar only at the first level
        blast_db_metadata = {}
        for line in soup.get_text().splitlines():
            items = [item for item in line.split(' ') if item != '']
            if len(items) != 4:
                continue
    
            # keeping only lines corresponding to .tar.gz files (not .md5)
            filename = items[0]
            if not filename.endswith('.tar.gz'):
                continue
                
            metadata = {
                'filename': filename,
                'last_updated': get_datetime(items[1], items[2], cls.BLAST_DATETIME_FORMAT),
                'size': items[3]
            }
            
            filename_parts = filename.split('.')
            blast_db_name = filename_parts[0]
            
            if len(filename_parts) == 3:
                blast_db_metadata[blast_db_name] = metadata
            elif len(filename_parts) == 4:
                blast_db_part = filename_parts[1]
                if blast_db_name not in blast_db_metadata:
                    blast_db_metadata[blast_db_name] = {}
                blast_db_metadata[blast_db_name][blast_db_part] = metadata
            else:
                logger.warning(f"Unexpected filename formatting for {filename}")
    
        return blast_db_metadata

    
    @classmethod
    def get_aggregated_metadata(cls, blast_db_metadata: dict) -> dict:
        result = {}
        for bladt_db_name, _dict in blast_db_metadata.items():
            # for databases without subparts, just getting the only values
            if 'filename' in _dict:
                result[bladt_db_name] = {
                    'version': _dict['last_updated'],
                    'n_parts': 1,
                    'mean_size': parse_size(_dict['size'])
                }
            else:
                # computing the last updated datetime as the most recent last update among all parts
                latest_update = max([subdict['last_updated'] for subdict in _dict.values()])
                mean_size = mean([parse_size(subdict['size']) for subdict in _dict.values()])
                result[bladt_db_name] = {
                    'version': latest_update,
                    'n_parts': len(_dict),
                    'mean_size': mean_size
                }
        return result


    @classmethod
    def download(cls, blast_db_metadata: dict, dest_dir: str, subdb_names: list[str] | None  = None):
        filenames = []
        for blast_db_name, _dict in blast_db_metadata.items():
            # filtering on the sub db name
            if subdb_names is not None and blast_db_name not in subdb_names:
                continue
            # for databases without subparts, just getting the only values
            if 'filename' in _dict:
                filenames.append(_dict['filename'])
            else:
                filenames += [subdict['filename'] for subdict in _dict.values()]
        # download
        for filename in filenames:
            url = cls.BLAST_DB_FTP_BASE_URL + filename
            cls.download_file(url, dest_dir)
            # checking md5
            md5_filename = filename + '.md5'
            md5_url = cls.BLAST_DB_FTP_BASE_URL + md5_filename
            cls.download_md5_and_checksum(md5_url, dest_dir)
            

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HELPER FUNCTIONS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def is_retryable(exception: BaseException) -> bool:
    """Retry everything except a 404 HTTPStatusError."""
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code != 404
    return True


@retry(
    retry=retry_if_exception(is_retryable),
    stop=stop_after_delay(600),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def parse_page_data(url: str) -> BeautifulSoup:
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        page = client.get(url)
        page.raise_for_status()
        return BeautifulSoup(page.content, "html.parser")


def get_datetime(date: str, time: str, fmt: str) -> datetime:
    date_time_str = f"{date} {time}"
    return datetime.strptime(date_time_str, fmt)


def parse_size(size_str: str) -> int:
    """
    Convert size strings like '902K', '4.1M', '5G' to bytes.

    Parameters:
    -----------
    size_str : str
        Size string with suffix (K, M, G, T, etc.)

    Returns:
    --------
    int : size in bytes
    """
    size_str = size_str.strip().upper()
    # Define multipliers
    MULTIPLIERS = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}
    # Check if last character is a unit
    if size_str[-1] in MULTIPLIERS:
        number = float(size_str[:-1])
        multiplier = MULTIPLIERS[size_str[-1]]
        return int(number * multiplier)
    else:
        # No suffix, assume it's already in bytes
        return int(float(size_str))