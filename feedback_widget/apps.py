from django.apps import AppConfig


class FeedbackWidgetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'feedback_widget'
    verbose_name = 'Feedback Widget'

    def ready(self):
        # Ensure the signal module is imported so listeners register
        from . import signals  # noqa: F401
