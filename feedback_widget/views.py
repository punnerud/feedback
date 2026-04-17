"""Views for django-feedback-widget.

- submit: JSON POST endpoint from the widget. Login required by default.
- admin_list / admin_detail / admin_delete: simple staff-only admin UI.

Extension points:
- FEEDBACK_LOGIN_REQUIRED setting (default True) — require auth to submit
- FEEDBACK_ADMIN_TEST — dotted path to a callable(user) -> bool that decides
  who may access admin views. Defaults to `is_staff`.
- Signal `feedback_widget.signals.feedback_submitted` — fires after save.
"""
import base64
import json
import logging
import uuid
from importlib import import_module

from django.conf import settings
from django.contrib.auth.decorators import login_required as _login_required
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from .models import Feedback, FeedbackScreenshot
from .signals import feedback_submitted

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Configuration helpers
# ------------------------------------------------------------------

def _login_required_decorator():
    """Resolve the project's login_required decorator.

    Falls back to django.contrib.auth if the project uses the standard one.
    Override via FEEDBACK_LOGIN_REQUIRED_DECORATOR setting (dotted path).
    """
    override = getattr(settings, 'FEEDBACK_LOGIN_REQUIRED_DECORATOR', None)
    if override:
        mod_path, _, func_name = override.rpartition('.')
        return getattr(import_module(mod_path), func_name)
    return _login_required


def _is_admin(user):
    """Decide if a user may view the admin feedback list.

    Override with FEEDBACK_ADMIN_TEST = 'path.to.callable'.
    Default: user.is_staff is True.
    """
    test_path = getattr(settings, 'FEEDBACK_ADMIN_TEST', None)
    if test_path:
        mod_path, _, func_name = test_path.rpartition('.')
        test = getattr(import_module(mod_path), func_name)
        return bool(test(user))
    return bool(getattr(user, 'is_staff', False))


def _max_shots():
    return int(getattr(settings, 'FEEDBACK_MAX_SHOTS', 3))


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

login_required = _login_required_decorator()


@csrf_protect
@login_required
def submit(request):
    """JSON POST endpoint invoked by the widget.

    Expected payload:
        {
          "kind": "bug" | "tips" | "question" | "other",
          "message": "...",
          "url": "https://...",
          "user_agent": "...",
          "screen_size": "1920x1080",
          "metadata": {...},   // optional, passed straight to Feedback.metadata
          "shots": [
              {"screenshot_b64": "data:image/png;base64,...", "url": "https://..."},
              ...
          ]
        }

    Response: {"ok": true, "feedback_id": N, "shots_saved": N, "shots_submitted": N,
               "shot_errors": [...], "warning": "..." | null}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    message = (data.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'Message is required.'}, status=400)

    kind = (data.get('kind') or 'bug').strip()
    valid_kinds = {k for k, _ in Feedback.KIND_CHOICES}
    if kind not in valid_kinds:
        kind = 'other'

    url = (data.get('url') or '')[:1000]
    user_agent = (data.get('user_agent') or '')[:2000]
    screen_size = (data.get('screen_size') or '')[:30]
    metadata = data.get('metadata') or {}
    if not isinstance(metadata, dict):
        metadata = {}

    fb = Feedback.objects.create(
        user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
        kind=kind,
        message=message,
        url=url,
        user_agent=user_agent,
        screen_size=screen_size,
        metadata=metadata,
    )

    # Shots — new multi-shot payload (list) takes precedence; fall back to the
    # single-shot legacy field for older widget integrations.
    shots_in = data.get('shots') or []
    if not shots_in and data.get('screenshot_b64'):
        shots_in = [{'screenshot_b64': data.get('screenshot_b64'), 'url': url}]

    shots_saved = 0
    shot_errors = []
    max_shots = _max_shots()

    for idx, s in enumerate(shots_in[:max_shots]):
        b64 = (s.get('screenshot_b64') or '')
        s_url = (s.get('url') or url or '')[:1000]
        if not b64 or not b64.startswith('data:image/'):
            shot_errors.append({'shot': idx + 1, 'reason': 'invalid image data'})
            continue
        try:
            header, body = b64.split(',', 1)
            raw = base64.b64decode(body)
            ext = 'png' if 'png' in header else 'jpg'
            fname = f'feedback-{fb.pk}-{idx+1}-{uuid.uuid4().hex[:8]}.{ext}'
            shot = FeedbackScreenshot(
                feedback=fb, url=s_url, sort_order=idx,
            )
            shot.image.save(fname, ContentFile(raw), save=True)
            shots_saved += 1
        except Exception as e:  # pragma: no cover — defensive
            logger.exception('Feedback %s: failed to save shot %s', fb.pk, idx + 1)
            shot_errors.append({'shot': idx + 1, 'reason': str(e)[:200]})

    # Notify listeners (e.g. ticket/case creation in downstream apps)
    try:
        feedback_submitted.send(
            sender=Feedback, feedback=fb, request=request,
        )
    except Exception:
        logger.exception('feedback_submitted signal listener raised')

    payload = {
        'ok': True,
        'feedback_id': fb.pk,
        'shots_submitted': len(shots_in[:max_shots]),
        'shots_saved': shots_saved,
        'shot_errors': shot_errors,
        'warning': None,
        'metadata': fb.metadata,
    }
    if shot_errors:
        payload['warning'] = (
            f'{payload["shots_submitted"] - shots_saved} of '
            f'{payload["shots_submitted"]} screenshots could not be saved.'
        )
    return payload_to_response(fb, payload)


def payload_to_response(fb, payload):
    """Allow downstream listeners to add fields to the response.

    Listeners that want to return a URL (e.g. the created ticket's URL) can set
    `fb.metadata['response_extras'] = {'ticket_url': '...'}` during the
    `feedback_submitted` signal; those keys are merged into the response.
    """
    extras = (fb.metadata or {}).get('response_extras') or {}
    if isinstance(extras, dict):
        payload.update(extras)
    return JsonResponse(payload)


# ------------------------------------------------------------------
# Admin UI
# ------------------------------------------------------------------

@login_required
def admin_list(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden()
    qs = Feedback.objects.select_related('user').prefetch_related('screenshots').order_by('-created_at')
    kind_filter = request.GET.get('kind', '')
    if kind_filter:
        qs = qs.filter(kind=kind_filter)
    return render(request, 'feedback_widget/admin_list.html', {
        'feedbacks': qs[:200],
        'kind_filter': kind_filter,
        'kind_choices': Feedback.KIND_CHOICES,
        'total': qs.count(),
    })


@login_required
def admin_detail(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden()
    fb = get_object_or_404(
        Feedback.objects.select_related('user').prefetch_related('screenshots'),
        pk=pk,
    )
    return render(request, 'feedback_widget/admin_detail.html', {'fb': fb})


@login_required
def admin_delete(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden()
    fb = get_object_or_404(Feedback, pk=pk)
    if request.method == 'POST':
        fb.delete()
        return redirect('feedback_widget:admin_list')
    return redirect('feedback_widget:admin_detail', pk=pk)
