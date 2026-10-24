from datetime import datetime
from pathlib import Path
from celery import shared_task
from django.core.cache import cache

from .models import Database, SyncRun


class AlreadyRunningException(Exception):
    pass


class NoNewerVersionAvailable(Exception):
    pass


def get_run_if_not_locked(db: Database, runtype: str) -> SyncRun:
    run = SyncRun.objects.get_or_create(db=db, runtype=runtype, status="running")
    lock = cache.lock(f"{run.type}:{db.name}", timeout=60 * 60 * 6)
    if not lock.acquire(blocking=False):
        raise AlreadyRunningException
    return run


def free_lock(run: SyncRun) -> None:
    cache.delete(f"{run.type}:{run.db.name}")


@shared_task(
    bind=True, 
    name="databases.tasks.check_database_updates",
    soft_time_limit=60 * 60 * 1
)
def check_database_updates(self, db: Database) -> None:
    run = get_run_if_not_locked(db, runtype="check")
    try:
        version = db.check_updates()
        db.last_checked_for_updates_at = datetime.now()
        if version != db.current_version:
            db.new_available_version = version
        db.save(update_fields=["last_checked_for_updates_at", "new_available_version"])
        run.status = "success"
        run.message = f"Got version: {version}"
    except Exception as exc:
        run.status, run.message = "failed", str(exc)
        raise
    finally:
        run.finished_at = datetime.now()
        run.save()
        free_lock(run)


@shared_task(
    bind=True, 
    name="databases.tasks.update_database",
    soft_time_limit=60 * 60 * 48
)
def update_database(self, db: Database) -> Path:
    """
    Ask the runner service to execute the database's download pipeline
    and poll it until completion. 
    A Redis lock prevents two concurrent pipelines for the same db.
    """
    run = get_run_if_not_locked(db, runtype="download")
    new_version = db.new_available_version
    if new_version is None:
        raise NoNewerVersionAvailable
        
    try:
        db_path = db.update()
        db.current_version = new_version
        db.new_available_version = None
        db.last_synced_at = datetime.now()
        db.save(update_fields=["current_version", "last_synced_at", "new_available_version"])
        run.status = "success"
        run.message = f"Successfully downloaded version {db.display_name} version {new_version}"
    except Exception as exc:
        run.status, run.message = "failed", str(exc)
        raise
    finally:
        run.finished_at = datetime.now()
        run.save()
        free_lock(run)
        
    return db_path
    