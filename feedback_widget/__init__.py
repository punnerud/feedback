"""django-feedback-widget — reusable feedback capture with screenshots.

Floating button + modal with html2canvas screen capture, redaction, highlight
spotlight, freehand pen, multi-shot (cross-page) and auto-save drafts.

Downstream apps hook into the `feedback_submitted` signal to convert feedback
into their own domain objects (tickets, cases, tasks, Slack messages, etc.).
"""
__version__ = '0.1.0'

default_app_config = 'feedback_widget.apps.FeedbackWidgetConfig'
