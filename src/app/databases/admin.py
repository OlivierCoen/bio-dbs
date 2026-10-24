from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from django_celery_beat.models import CrontabSchedule, PeriodicTask

from .models import Database, SyncRun
from .tasks import check_updates

class SyncRunInline(admin.TabularInline):
    model = SyncRun
    extra = 0
    can_delete = False
    fields = ("status", "started_at", "finished_at", "message")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Database)
class DatabaseAdmin(admin.ModelAdmin):
    list_display = (
        "name", 
        "enabled",
        "current_version", 
        "last_synced_at",
        "auto_update", 
        "schedule_link"
    )
    inlines = (SyncRun)
    actions = (
        "check_updates_of_databases",
        "update_databases" ,
    )

    @admin.action(description="Check database updates")
    def check_updates_of_databases(self, request, queryset):
        for db in queryset:
            check_updates.delay(db)


    @admin.action(description="Update database(s)")
    def update_databases(self, request, queryset):
        for db in queryset:
            check_updates.delay(db)
            

    @admin.action(description="Create planning")
    def create_schedule(self, request, queryset):
        cron, _ = CrontabSchedule.objects.get_or_create(
            minute="0", 
            hour="3", 
            day_of_week="*",
            day_of_month="*", 
            month_of_year="*"
        )
        for db in queryset:
            PeriodicTask.objects.update_or_create(
                name=f"check-{db.name}",
                defaults={
                    'task': "databases.tasks.check_updates",
                    'crontab': cron,
                    'enabled': True,
                    'args': [db.id],
                })

    @admin.display(description="Planning")
    def schedule_link(self, obj):
        task = PeriodicTask.objects.filter(name=f"check-{obj.name}").first()
        if not task:
            return "—"
        url = reverse("admin:djcelery_periodictask_change", args=[task.pk])
        return format_html(
            '<a href="{}">{}</a>', 
            url,
            "✅ actif" if task.enabled else "⏸ inactif"
        )


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "db", 
        "status", 
        "version_found",
        "started_at",
        "finished_at"
    )
    list_filter = ("db", "status")
    readonly_fields = [f.name for f in SyncRun._meta.fields]
