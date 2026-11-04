from django.http import HttpResponse
from django.urls import URLResolver, get_resolver, include, path
from django.views import View
from rest_framework import viewsets
from rest_framework.routers import SimpleRouter
from rest_framework.views import APIView

from apps.core.csrf import CsrfEnforcedMixin
from apps.users.views import RegisterView

UNSAFE_METHODS = ("post", "put", "patch", "delete")


def callbacks(patterns):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from callbacks(pattern.url_patterns)
        else:
            yield pattern.callback


def unsafe_methods_served(callback):
    view_class = callback.view_class
    # as_view() puede cambiar los métodos admitidos sin tocar la clase
    names = callback.view_initkwargs.get(
        "http_method_names", view_class.http_method_names
    )
    return [m for m in UNSAFE_METHODS if m in names and hasattr(view_class, m)]


def check_views(patterns):
    checked, unguarded = [], []
    for callback in callbacks(patterns):
        view_class = getattr(callback, "view_class", None)
        # De una función no se sabe qué métodos atiende: no puede darse por segura
        if view_class is None:
            unguarded.append(callback)
        elif unsafe_methods_served(callback):
            checked.append(view_class)
            if not issubclass(view_class, CsrfEnforcedMixin):
                unguarded.append(view_class)
    return checked, unguarded


def project_patterns():
    return get_resolver("config.urls").url_patterns


def test_every_project_view_that_changes_state_has_the_explicit_csrf_check():
    _, unguarded = check_views(project_patterns())

    assert unguarded == []


def test_the_walk_reaches_the_registration_view():
    checked, _ = check_views(project_patterns())

    assert RegisterView in checked


# Vistas sintéticas: prueban la guarda sin tocar el URLconf real


class Anonymous:
    authentication_classes = []
    permission_classes = []


class UnguardedPost(Anonymous, APIView):
    def post(self, request):
        return HttpResponse()


class UnguardedDelete(Anonymous, APIView):
    def delete(self, request):
        return HttpResponse()


class GuardedPost(Anonymous, CsrfEnforcedMixin, APIView):
    def post(self, request):
        return HttpResponse()


class ReadOnly(Anonymous, APIView):
    def get(self, request):
        return HttpResponse()


class HandlerNotListed(Anonymous, APIView):
    http_method_names = ["get"]

    def get(self, request):
        return HttpResponse()

    def post(self, request):
        return HttpResponse()


class DjangoPost(View):
    def post(self, request):
        return HttpResponse()


def function_view(request):
    return HttpResponse()


class GuardedViewSet(Anonymous, CsrfEnforcedMixin, viewsets.ViewSet):
    def create(self, request):
        return HttpResponse()


def test_the_guard_flags_a_state_changing_view_without_the_mixin():
    _, unguarded = check_views([path("a/", UnguardedPost.as_view())])

    assert unguarded == [UnguardedPost]


def test_the_guard_looks_inside_nested_includes():
    patterns = [
        path(
            "outer/",
            include([path("inner/", include([path("b/", UnguardedDelete.as_view())]))]),
        )
    ]

    _, unguarded = check_views(patterns)

    assert unguarded == [UnguardedDelete]


def test_the_guard_flags_a_plain_django_view_that_accepts_post():
    _, unguarded = check_views([path("a/", DjangoPost.as_view())])

    assert unguarded == [DjangoPost]


def test_the_guard_flags_a_function_view_it_cannot_inspect():
    _, unguarded = check_views([path("a/", function_view)])

    assert unguarded == [function_view]


def test_the_guard_flags_a_viewset_even_with_the_mixin():
    # Una ViewSet no expone view_class: sin poder inspeccionarla no se da por segura
    router = SimpleRouter()
    router.register("things", GuardedViewSet, basename="things")

    _, unguarded = check_views(router.urls)

    assert [callback.cls for callback in unguarded] == [GuardedViewSet]


def test_the_guard_accepts_views_with_the_mixin_or_without_unsafe_methods():
    patterns = [
        path("guarded/", GuardedPost.as_view()),
        path("read-only/", ReadOnly.as_view()),
        path("not-listed/", HandlerNotListed.as_view()),
        path("narrowed/", UnguardedPost.as_view(http_method_names=["get"])),
    ]

    checked, unguarded = check_views(patterns)

    assert unguarded == []
    assert checked == [GuardedPost]
