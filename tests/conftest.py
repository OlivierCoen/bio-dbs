import pytest
import fakeredis
from databases.models import Database

@pytest.fixture(autouse=True)
def fake_lock_redis(monkeypatch):
    """All tasks use an in-memory Redis during tests."""
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr("databases.tasks._lock_client", fake)
    yield fake

@pytest.fixture
def blast_db(db) -> Database:
    return Database.objects.create(
        name="blast", display_name="Blast", enabled=True
    )