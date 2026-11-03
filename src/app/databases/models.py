from django.db import models
from pathlib import Path
from typing import ClassVar

from modules.base import BaseModule


class Database(models.Model):
    """A data db to mirror (RefSeq, UniProt, PDB...)."""

    name = models.SlugField(unique=True)
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
    new_available_version = models.CharField(max_length=100, null=True, blank=True)
    last_checked_for_updates_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def module_cls(self) -> type[BaseModule]:
        """
        Get module class associated to the database name.
        """
        from modules.registry import discover_modules
        registry = discover_modules()
        try:
            return registry[self.name]
        except KeyError:
            raise self.ModuleNotFound(
                f"No module '{self.name}' found (available: {sorted(registry)})"
            )
    
    def check_updates(self) -> dict:
        return self.module_cls().check_updates()

    def update(self, dest_path: str, subdb_names: list[str] | None = None) -> None:
        return self.module_cls().update(
            dest_path,
            self.new_available_version,
            subdb_names if subdb_names is not None else []
        )

    def __str__(self):
        return self.display_name


class SubDatabase(models.Model):
    
    database = models.ForeignKey(Database, on_delete=models.CASCADE, related_name="sub_databases")
    name = models.SlugField()
    n_parts = models.IntegerField(null=True, blank=True)
    mean_size = models.BigIntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=False)
    current_version = models.CharField(max_length=100, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("database", "name")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_parent_enabled()

    def _sync_parent_enabled(self) -> None:
        """Keep the parent Database in sync with its sub-databases:
        enabled as soon as one sub-db is enabled, disabled when none are."""
        parent = self.database
        has_enabled = parent.sub_databases.filter(enabled=True).exists()
        if parent.enabled != has_enabled:
            parent.enabled = has_enabled
            parent.save(update_fields=["enabled"])

    def __str__(self):
        return self.name


class SyncRun(models.Model):
    """One synchronisation execution (check or download)."""

    STATUSES: ClassVar[dict[str, str]] = {
        "pending": "Pending", 
        "running": "Running",
        "success": "Success", 
        "failed": "Failed",
        "skipped": "Skipped"
    }

    CHECK_UPDATES_TIMEOUT: ClassVar[int] = 60 * 60 * 1
    UPDATE_TIMEOUT: ClassVar[int] = 60 * 60 * 48

    class Type(models.TextChoices):
        CHECK = "check_updates", 'Check database updates'
        DOWNLOAD = "update", 'Update database'

    
    type = models.CharField(max_length=20, choices=Type.choices)
    database = models.ForeignKey(Database, on_delete=models.CASCADE, related_name="runs")
    sub_database = models.ForeignKey(
        SubDatabase, on_delete=models.CASCADE, null=True, blank=True
    ) # null = the Database object itself / non-null = a specific subdatabase
    status = models.CharField(max_length=10, choices=STATUSES, default="pending")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_update_permission(self, request, obj=None):
        return False

    class Meta:
        ordering = ["-started_at"]
