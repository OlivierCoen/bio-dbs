from typing import ClassVar
from base import DatabaseTest
from databases.models import SubDatabase


class BlastTest(DatabaseTest):

    NAME: ClassVar[str] = "blast"

    def test_check_updates(self):
        latest_version_metadata = self.db.check_updates()
        print(latest_version_metadata)

    def test_update(self):
        enabled_subdbs = ['16S_ribosomal_RNA']
        for subdb_name in enabled_subdbs:
            SubDatabase.objects.create(name=subdb_name, database=self.db)
        dest_path = self.get_dest_path()
        self.db.update(dest_path, enabled_subdbs)