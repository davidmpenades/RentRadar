from django.utils.cache import cc_delim_re


def mark_response_cookieless(response):
    response.cookieless = True
    return response


class CleanMarkedResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Solo el True exacto: una marca truthy cualquiera no basta para borrar cookies
        if getattr(response, "cookieless", False) is True:
            response.cookies.clear()
            self._remove_cookie_from_vary(response)
        return response

    @staticmethod
    def _remove_cookie_from_vary(response):
        if "Vary" not in response:
            return
        tokens = [token.strip() for token in cc_delim_re.split(response["Vary"])]
        tokens = [token for token in tokens if token and token.lower() != "cookie"]
        if tokens:
            response["Vary"] = ", ".join(tokens)
        else:
            del response["Vary"]
