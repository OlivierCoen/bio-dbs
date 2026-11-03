import pytest
from databases.models import Database, SubDatabase

@pytest.mark.django_db
def test_enabling_subdb_enables_parent(blast_db):
    sub = SubDatabase.objects.create(database=blast_db, name="nt", enabled=False)
    assert not blast_db.enabled
    sub.enabled = True
    sub.save()
    blast_db.refresh_from_db()
    assert blast_db.enabled

@pytest.mark.django_db
def test_all_subdbs_disabled_disables_parent(blast_db):
    blast_db.enabled = True
    blast_db.save()
    sub = SubDatabase.objects.create(database=blast_db, name="nt", enabled=False)
    sub.save()
    blast_db.refresh_from_db()
    assert not blast_db.enabled