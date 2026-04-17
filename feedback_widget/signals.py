"""Dispatch signals for feedback-widget.

Downstream apps can listen to `feedback_submitted` to create domain objects
(support tickets, CRM cases, Slack notifications, GitHub issues, etc.)
without modifying this package.

Example listener in your own app:

    from django.dispatch import receiver
    from feedback_widget.signals import feedback_submitted

    @receiver(feedback_submitted)
    def create_support_ticket(sender, feedback, request, **kwargs):
        SupportTicket.objects.create(
            title=feedback.message[:80],
            description=feedback.message,
            reporter=feedback.user,
        )
"""
from django.dispatch import Signal


# Sent after a Feedback + all screenshots have been saved.
# Arguments: sender (Feedback class), feedback (instance), request (HttpRequest or None)
feedback_submitted = Signal()
