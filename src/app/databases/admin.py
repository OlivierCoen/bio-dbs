import logging
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from django_celery_beat.models import CrontabSchedule, PeriodicTask

from .models import Database, SubDatabase, SyncRun
from .tasks import check_database_updates, update_database

logger = logging.getLogger(__name__)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# INLINE CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SyncRunInline(admin.TabularInline):
    model = SyncRun
    extra = 0
    can_delete = False
    fields = ("status", "started_at", "finished_at", "message")
    readonly_fields = fields

    def has_change_permission(self, request, obj=None):
        return False


class SubDatabaseInline(admin.TabularInline):
    model = SubDatabase
    extra = 0
    can_delete = False
    fields = ("name", "enabled", "current_version", "last_synced_at")
    readonly_fields = ("current_version", "last_synced_at")
    

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ADMIN CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@admin.register(Database)
class DatabaseAdmin(admin.ModelAdmin):
    list_display = (
        "name", 
        "enabled",
        "n_sub_databases",
        "current_version", 
        "last_synced_at",
        "auto_update", 
        "schedule_link"
    )
    inlines = [
        SubDatabaseInline,
        SyncRunInline,
    ]
    actions = (
        "check_updates_of_databases",
        "update_databases" ,
    )

    list_filter = ("name", "enabled", "last_synced_at", "auto_update")
    readonly_fields = ("name", "n_sub_databases", "last_synced_at", "schedule_link")

    @admin.action(description="Check updates of database(s)")
    def check_updates_of_databases(self, request, queryset):
        for db in queryset:
            check_database_updates.delay(db.id)


    @admin.action(description="Update database(s)")
    def update_databases(self, request, queryset):
        for db in queryset:
            update_database.delay(db.id)
            

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
        url = reverse("admin:django_celery_beat_periodictask_change", args=[task.id])
        return format_html(
            '<a href="{}">{}</a>', 
            url,
            "✅ actif" if task.enabled else "⏸ inactif"
        )

    @admin.display(description="Sub-databases")
    def n_sub_databases(self, obj):
        return obj.sub_databases.count()


@admin.register(SubDatabase)
class SubDatabaseAdmin(admin.ModelAdmin):
    list_display = (
        "database", 
        "name", 
        "n_parts",
        "mean_size",
        "enabled",
        "current_version", 
        "last_synced_at"
    )
    list_filter = ("database", "name", "enabled", "last_synced_at")
    search_fields = ("name", "database")
    actions = ("download_selected", "check_updates_selected")
    readonly_fields = [f.name for f in SubDatabase._meta.concrete_fields]

    @admin.action(description="Update sub-database(s)")
    def check_updates_of_subdatabases(self, request, queryset):
        for sub in queryset:
            check_database_updates.delay(sub.db.id, sub.id)

    @admin.action(description="Update database(s)")
    def update_subdatabases(self, request, queryset):
        for sub in queryset:
            update_database.delay(sub.db.id, sub.id)


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "db", 
        "type",
        "status", 
        "started_at",
        "finished_at",
        "message"
    )
    list_filter = ("db", "status")
    readonly_fields = [f.name for f in SyncRun._meta.concrete_fields]
