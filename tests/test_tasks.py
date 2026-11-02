import pytest
from databases.tasks import check_database_updates, AlreadyRunning, SyncRun

def test_lock_prevents_concurrent_run(fake_lock_redis, blast_db, db):
    fake_lock_redis.lock(
        f"sync:check_updates:{blast_db.name}", 
        timeout=SyncRun.UPDATE_TIMEOUT,
        blocking_timeout=0
    ).acquire()
    with pytest.raises(AlreadyRunning):
        check_database_updates(blast_db.pk)

@pytest.mark.django_db
def test_check_updates_creates_run(blast_db):
    check_database_updates(blast_db.pk)
    assert blast_db.sync_runs.filter(status="success").exists()
    