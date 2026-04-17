"""Models for django-feedback-widget.

Feedback holds the submission; FeedbackScreenshot is a 1..N child so a single
Feedback can have multiple screenshots (one per page the user annotated).

`metadata` is a JSONField for downstream apps to attach context without
modifying this package (e.g. `{"case_id": 123, "project": "acme"}`).
"""
from django.conf import settings
from django.db import models


def _screenshot_upload_path(instance, filename):
    """Default upload path. Override via FEEDBACK_SCREENSHOT_UPLOAD_TO setting."""
    custom = getattr(settings, 'FEEDBACK_SCREENSHOT_UPLOAD_TO', None)
    if callable(custom):
        return custom(instance, filename)
    prefix = getattr(settings, 'FEEDBACK_UPLOAD_PREFIX', 'feedback')
    return f'{prefix}/%Y/%m/{filename}'.replace(
        '%Y', str(instance.feedback.created_at.year if instance.feedback_id else '0000')
    ).replace(
        '%m', f'{instance.feedback.created_at.month:02d}' if instance.feedback_id else '00'
    )


class Feedback(models.Model):
    """A user-submitted feedback item — bug, tip, question, or other."""
    KIND_CHOICES = [
        ('bug', 'Bug'),
        ('tips', 'Tip / suggestion'),
        ('question', 'Question'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='submitted_feedback_widget_items',
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='bug')
    message = models.TextField()
    url = models.CharField(max_length=1000, blank=True, default='')
    user_agent = models.TextField(blank=True, default='')
    screen_size = models.CharField(max_length=30, blank=True, default='')
    # Free-form metadata for downstream integrations. Example keys: company_id,
    # project, ticket_id, external_ref, severity, etc.
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'

    def __str__(self):
        return f'Feedback #{self.pk} — {self.kind}'


class FeedbackScreenshot(models.Model):
    """A single screenshot attached to a Feedback (0..N)."""
    feedback = models.ForeignKey(
        Feedback, on_delete=models.CASCADE, related_name='screenshots',
    )
    image = models.FileField(upload_to=_screenshot_upload_path)
    url = models.CharField(
        max_length=1000, blank=True, default='',
        help_text='URL where the screenshot was captured.',
    )
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return f'Screenshot #{self.pk} (feedback {self.feedback_id})'
