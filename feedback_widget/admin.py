from django.contrib import admin
from .models import Feedback, FeedbackScreenshot


class FeedbackScreenshotInline(admin.TabularInline):
    model = FeedbackScreenshot
    extra = 0
    readonly_fields = ('image', 'url', 'sort_order', 'created_at')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'user', 'message_preview', 'url', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('message', 'url', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'user_agent', 'screen_size', 'url', 'metadata')
    inlines = [FeedbackScreenshotInline]
    date_hierarchy = 'created_at'

    @admin.display(description='Message')
    def message_preview(self, obj):
        return (obj.message[:80] + '…') if len(obj.message) > 80 else obj.message


@admin.register(FeedbackScreenshot)
class FeedbackScreenshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'feedback', 'url', 'sort_order', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = ('feedback', 'image', 'url', 'sort_order', 'created_at')
