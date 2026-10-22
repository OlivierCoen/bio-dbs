from datetime import datetime

import httpx
from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from .models import Database, SyncRun


def _remote_version(db: Database) -> str | None:
    """Naive example: read a RELEASE file on the source.
    Adapt per bank (FTP listing, checksums, release notes...)."""
    resp = httpx.get(db.source_url.rstrip("/") + "/RELEASE",
                        timeout=60)
    resp.raise_for_status()
    return resp.text.strip() or None


@shared_task(bind=True, name="banks.tasks.check_updates")
def check_updates(self, bank_id: int):
    """Scheduled by django-celery-beat. Checks the remote version and
    triggers a pipeline run on the runner service if a new release exists."""
    bank = Database.objects.get(pk=bank_id)
    run = SyncRun.objects.create(bank=bank, status="running")

    try:
        remote = _remote_version(bank)
        if remote == bank.current_version:
            run.status, run.message = "skipped", f"Version {remote} unchanged"
            run.version_found = remote
        elif bank.auto_update:
            run.version_found = remote
            run.status = "success"
            run.message = f"New version {remote} -> pipeline run"
            run_pipeline.delay(bank_id, remote)
        else:
            run.status = "skipped"
            run.version_found = remote
            run.message = f"New version {remote} (auto_update disabled)"
    except Exception as exc:
        run.status, run.message = "failed", str(exc)
        raise
    finally:
        run.finished_at = datetime.now()
        run.save()

    return run.status


@shared_task(bind=True, name="banks.tasks.run_pipeline",
             soft_time_limit=60 * 60 * 10)
def run_pipeline(self, bank_id: int, version: str):
    """Ask the runner service to execute the bank's Nextflow pipeline
    and poll it until completion. A Redis lock prevents two concurrent
    pipelines for the same bank."""
    bank = Database.objects.get(pk=bank_id)
    lock = cache.lock(f"download:{bank.name}", timeout=60 * 60 * 6)
    if not lock.acquire(blocking=False):
        return "already_running"

    run = SyncRun.objects.create(bank=bank, status="running",
                                 version_found=version)
    try:
        with httpx.Client(timeout=30) as client:
            # Submit the job
            job = client.post(f"{settings.RUNNER_URL}/jobs", json={
                "pipeline": bank.pipeline,
                "bank": bank.name,
                "version": version,
                "params": {"source_url": bank.source_url},
            }).raise_for_status().json()
            job_id = job["job_id"]

            # Poll until done (a webhook callback would be cleaner)
            while True:
                state = client.get(
                    f"{settings.RUNNER_URL}/jobs/{job_id}").json()
                if state["status"] in ("success", "failed"):
                    if state["status"] == "failed":
                        raise RuntimeError(state.get("log", "pipeline failed"))
                    break
                self.refresh_cache()  # keep Celery soft-time-limit honest
                import time; time.sleep(30)

        bank.current_version = version
        bank.last_synced_at = datetime.now()
        bank.save(update_fields=["current_version", "last_synced_at"])
        run.status = "success"
    except Exception as exc:
        run.status, run.message = "failed", str(exc)
        raise
    finally:
        run.finished_at = datetime.now()
        run.save()
        cache.delete(f"download:{bank.name}")
    return run.status