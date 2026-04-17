# django-feedback-widget

Drop-in feedback capture for Django projects. Floating button + modal with
**screenshot capture** (html2canvas), **redaction**, **highlight spotlight**,
**freehand drawing**, **multi-page capture** (cross-navigation), and
**auto-save drafts**.

No third-party SaaS — screenshots stay on your own storage. Downstream apps
hook into a `feedback_submitted` signal to create tickets, CRM cases, Slack
messages, or whatever you want.

## Features

- One-click screenshot via `html2canvas` (bundled from CDN, no build step)
- Configurable countdown timer (0 / 3 / 5 / 10 / 20 / 30 sec) for capturing
  hover states, menus, etc. — countdown persists across page navigation
- In-browser editor:
  - Redaction (solid black rectangles)
  - Highlight (spotlight — dims rest of image)
  - Freehand drawing with 4 colors
  - Crop (one-shot)
  - Draggable + resizable boxes, double-click to delete
- Up to 3 screenshots per submission (configurable)
- Auto-save to `localStorage` — survives navigation and tab crashes
- Multiple URLs captured per submission (one per screenshot)
- Mobile-friendly (touch events, 40×40 px targets)
- Bootstrap 5 compatible (you provide the CSS)
- I18n-ready via Django `gettext`

## Installation

```bash
pip install django-feedback-widget
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'feedback_widget',
]
```

Include URLs:

```python
# urls.py
urlpatterns = [
    # ...
    path('feedback/', include('feedback_widget.urls')),
]
```

Run migrations:

```bash
python manage.py migrate
```

Include the widget in your base template, wherever you want the floating
button to appear (usually in the navbar or just before `</body>`):

```html
{% if request.user.is_authenticated %}
{% include "feedback_widget/widget.html" %}
{% endif %}
```

Make sure Bootstrap 5 JS (`bootstrap.bundle.min.js`) is loaded **before** the
widget's `<script>` runs. The widget uses lazy Modal initialization so it
works even if Bootstrap loads after the widget's inline script.

## Settings

All optional:

| Setting | Default | Description |
|---|---|---|
| `FEEDBACK_MAX_SHOTS` | `3` | Max screenshots per submission |
| `FEEDBACK_LOGIN_REQUIRED_DECORATOR` | `django.contrib.auth.decorators.login_required` | Dotted path to a decorator; override if you use a custom auth flow |
| `FEEDBACK_ADMIN_TEST` | (none — `user.is_staff`) | Dotted path to `callable(user) -> bool` that decides admin list access |
| `FEEDBACK_UPLOAD_PREFIX` | `'feedback'` | Upload-to prefix inside `MEDIA_ROOT` |
| `FEEDBACK_SCREENSHOT_UPLOAD_TO` | (none) | Optional callable `(instance, filename)` returning an upload path |

## Extension signal

Listen to `feedback_submitted` to integrate with your domain logic:

```python
# my_app/signals.py
from django.dispatch import receiver
from feedback_widget.signals import feedback_submitted

@receiver(feedback_submitted)
def create_support_ticket(sender, feedback, request, **kwargs):
    """Turn every feedback submission into a support ticket."""
    from my_app.models import Ticket
    ticket = Ticket.objects.create(
        title=feedback.message.splitlines()[0][:80] or 'Feedback',
        description=feedback.message,
        reporter=feedback.user,
        external_ref=f'feedback:{feedback.pk}',
    )
    # Optional: echo data back to the widget UI via response_extras
    feedback.metadata['response_extras'] = {
        'ticket_url': ticket.get_absolute_url(),
        'ticket_id': ticket.pk,
    }
    feedback.save(update_fields=['metadata'])

    # Attach screenshots to the ticket
    for shot in feedback.screenshots.all():
        ticket.attachments.create(
            file=shot.image,
            description=f'Screenshot from {shot.url}',
        )
```

Remember to import the signal module from your `AppConfig.ready()` so the
receiver registers.

## Admin

Staff users can browse submissions at `/feedback/admin/`. Override who counts
as "admin" via `FEEDBACK_ADMIN_TEST`:

```python
FEEDBACK_ADMIN_TEST = 'my_app.auth.can_view_feedback'
```

Also registered with Django's built-in admin at `/admin/feedback_widget/`.

## Example project

See `example/` for a minimal Django project that integrates the widget.

```bash
cd example
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then visit http://127.0.0.1:8000 and log in — the widget button appears in
the navbar.

## Data model

```
Feedback
├── id
├── user (FK, nullable)
├── kind (bug / tips / question / other)
├── message (TextField)
├── url (where the user was when submitting)
├── user_agent, screen_size
├── metadata (JSONField — for your integration data)
└── created_at

FeedbackScreenshot (1..N)
├── feedback (FK)
├── image (FileField)
├── url (where this particular screenshot was taken)
├── sort_order
└── created_at
```

## License

MIT
