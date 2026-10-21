from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET


@require_GET
def only_get(request):
    return HttpResponse("ok")


def explode(request):
    raise RuntimeError("SELECT secret FROM users /app/config/settings/base.py")


def start_session(request):
    request.session["visited"] = True
    get_token(request)
    return HttpResponse("ok")


def leak(request):
    raise RuntimeError(request.GET["message"])
