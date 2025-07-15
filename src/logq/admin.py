from django.contrib import admin

from .models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'level', 'message')
    list_filter = ('level', 'timestamp')
    search_fields = ('message',)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)