from django.utils import timezone
from celery import shared_task
from django.conf import settings
import redis
from redis.exceptions import LockNotOwnedError
import logging

from .models import Database, SubDatabase, SyncRun

logger = logging.getLogger(__name__)

_lock_client = redis.Redis.from_url(settings.CACHES["default"]["LOCATION"])


class AlreadyRunning(Exception):
    pass


class NoNewerVersionAvailable(Exception):
    pass


def get_sync_run(db: Database, run_type: str):
    run, _created = SyncRun.objects.get_or_create(db=db, type=run_type, status="running")
    return run


def get_lock(db: Database, run_type: str):
    lock = _lock_client.lock(
        f"sync:{run_type}:{db.name}",
        timeout=SyncRun.UPDATE_TIMEOUT,
        blocking_timeout=0,
    )
    if not lock.acquire():
        raise AlreadyRunning(f"Sync '{run_type}' already running for database {db.name}...")
    return lock
    

def release_lock(lock):
    try:
        lock.release()
    except LockNotOwnedError:
        logger.warning(f"Lock {lock.name} already expired, nothing to release")


@shared_task(
    bind=True, 
    name="databases.tasks.check_database_updates",
    soft_time_limit=SyncRun.CHECK_UPDATES_TIMEOUT
)
def check_database_updates(self, db_id: int, sub_db_id: int | None = None) -> None:
    db = Database.objects.get(id=db_id)
    run = get_sync_run(db, "check_updates")
    lock = get_lock(db, "check_updates")
        
    try:
        logger.info(f"Checking updates {db_id} {sub_db_id}")
        latest_version_metadata = db.check_updates()
        logger.info(f"Obtained: {latest_version_metadata}")
        
        version_list = []
        for sub_db_name, metadata in latest_version_metadata.items():
            sub_db, created = SubDatabase.objects.get_or_create(
                database=db,
                name=sub_db_name
            )
            if created:
                logger.info(f"Created sub-database {sub_db.name}")
                
            sub_db.current_version = metadata['version']
            sub_db.n_parts = metadata['n_parts']
            sub_db.mean_size = metadata['mean_size']
            sub_db.save()
            # storing the date of the last update
            version_list.append(metadata['version'])
        
        version = max(version_list)
        db.last_checked_for_updates_at = timezone.now()
        if version != db.current_version:
            db.new_available_version = version
            
        db.save(update_fields=["last_checked_for_updates_at", "new_available_version"])
        run.status = "success"
        run.message = f"Got version: {version}"
        
    except Exception as exc:
        run.status = "failed"
        run.message = str(exc)
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()
        release_lock(lock)


@shared_task(
    bind=True, 
    name="databases.tasks.update_database",
    soft_time_limit=SyncRun.UPDATE_TIMEOUT
)
def update_database(self, db_id: int):
    """
    Ask the runner service to execute the database's download pipeline
    and poll it until completion. 
    A Redis lock prevents two concurrent pipelines for the same db.
    """
    db = Database.objects.get(id=db_id)
    run = get_sync_run(db, "update")
    lock = get_lock(db, "update")

    
    new_version = db.new_available_version
    """
    if new_version is None:
        raise NoNewerVersionAvailable(f"No newer version available for database {db.name}")
    """
        
    try:
        enabled_subdbs = SubDatabase.objects.filter(database=db, enabled=True) 
        enabled_subdb_names = [subdb.name for subdb in enabled_subdbs]
        logger.info(f"Updating {db_id} (sub-databases: {' '.join(enabled_subdb_names)})")
        db.update(settings.DB_DIR, enabled_subdb_names)
        logger.info("Done")
        db.current_version = new_version
        db.new_available_version = None
        db.last_synced_at = timezone.now()
        db.save(update_fields=["current_version", "last_synced_at", "new_available_version"])
        run.status = "success"
        run.message = f"Successfully downloaded version {db.display_name} version {new_version}"
    except Exception as exc:
        run.status = "failed"
        run.message = str(exc)
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()
        release_lock(lock)
    