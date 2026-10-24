from django.db import models
from pathlib import Path
from typing import ClassVar

from modules.base import Module


class Database(models.Model):
    """A data db to mirror (RefSeq, UniProt, PDB...)."""

    name = models.SlugField(unique=True)              # "refseq", "uniprot_sprot"
    display_name = models.CharField(max_length=200)
    enabled = models.BooleanField(
        default=False,
        help_text="If true, integrate the database in the update system"
    )
    auto_update = models.BooleanField(
        default=False,
        help_text="If false, a new remote version does not trigger a download"
    )
    current_version = models.CharField(max_length=100, blank=True)
    new_available_version = models.CharField(max_length=100, blank=True)
    last_checked_for_updates_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    # associate a module class to this database
    _module: type[Module]
    

    def __str__(self):
        return self.display_name


    def check_updates(self) -> str:
        return self._module.check_updates()

    def update(self) -> Path:
        return self._module.update(self.new_available_version)


class SyncRun(models.Model):
    """One execution (check or download)."""

    TYPES: ClassVar[tuple] = ('check', 'download')

    STATUSES: ClassVar[tuple[tuple[str, str], ...]] = (
        ("pending", "Pending"), 
        ("running", "Running"),
        ("success", "Success"), 
        ("failed", "Failed"),
        ("skipped", "No change")
    )

    db = models.ForeignKey(Database, on_delete=models.CASCADE, related_name="runs")
    type = models.CharField(max_length=10, choices=TYPES)
    status = models.CharField(max_length=10, choices=STATUSES, default="pending")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
