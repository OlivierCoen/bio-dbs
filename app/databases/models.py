from django.db import models


class Database(models.Model):
    """A data bank to mirror (RefSeq, UniProt, PDB...)."""

    name = models.SlugField(unique=True)              # "refseq", "uniprot_sprot"
    display_name = models.CharField(max_length=200)
    source_url = models.URLField(help_text="Source FTP/HTTP URL")
    # Nextflow pipeline to run for a full download (relative to pipelines/)
    pipeline = models.CharField(max_length=200, default="refseq.nf")
    current_version = models.CharField(max_length=100, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    auto_update = models.BooleanField(default=True,
        help_text="If false, a new remote version does not trigger a download")

    def __str__(self):
        return self.display_name


class SyncRun(models.Model):
    """One execution (check or download)."""

    STATUS = [("pending", "Pending"), ("running", "Running"),
              ("success", "Success"), ("failed", "Failed"),
              ("skipped", "No change")]

    bank = models.ForeignKey(Database, on_delete=models.CASCADE,
                              related_name="runs")
    status = models.CharField(max_length=10, choices=STATUS,
                              default="pending")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    version_found = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]