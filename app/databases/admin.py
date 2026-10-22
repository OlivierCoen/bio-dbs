from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from django_celery_beat.models import CrontabSchedule, PeriodicTask

from .models import Database, SyncRun


class SyncRunInline(admin.TabularInline):
    model = SyncRun
    extra = 0
    can_delete = False
    fields = ("status", "version_found", "started_at", "finished_at",
              "message")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Database)
class DatabaseAdmin(admin.ModelAdmin):
    list_display = ("name", "current_version", "last_synced_at",
                    "auto_update", "schedule_link")
    inlines = [SyncRunInline]
    actions = ["sync_now", "create_schedule"]

    @admin.action(description="Lancer un check + download maintenant")
    def sync_now(self, request, queryset):
        from .tasks import check_updates
        for bank in queryset:
            check_updates.delay(bank.id)

    @admin.action(description="Créer le planning quotidien (3h du matin)")
    def create_schedule(self, request, queryset):
        from django_celery_beat.models import (CrontabSchedule,
                                               PeriodicTask)
        cron, _ = CrontabSchedule.objects.get_or_create(
            minute="0", hour="3", day_of_week="*",
            day_of_month="*", month_of_year="*")
        for bank in queryset:
            PeriodicTask.objects.update_or_create(
                name=f"check-{bank.name}",
                defaults=dict(
                    task="banks.tasks.check_updates",
                    crontab=cron,
                    enabled=True,
                    args=[bank.id],
                ))

    @admin.display(description="Planning")
    def schedule_link(self, obj):
        task = PeriodicTask.objects.filter(name=f"check-{obj.name}").first()
        if not task:
            return "—"
        url = reverse("admin:djcelery_periodictask_change",
                      args=[task.pk])
        return format_html('<a href="{}">{}</a>', url,
                           "✅ actif" if task.enabled else "⏸ inactif")


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ("bank", "status", "version_found",
                    "started_at", "finished_at")
    list_filter = ("bank", "status")
    readonly_fields = [f.name for f in SyncRun._meta.fields]
