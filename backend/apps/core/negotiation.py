from rest_framework.negotiation import DefaultContentNegotiation


# DRF resuelve esta clase al importar rest_framework.views: aquí no se importa DRF views
class JSONOnlyNegotiation(DefaultContentNegotiation):
    # Siempre JSON: Accept no provoca un 406 ni añade Vary
    def select_renderer(self, request, renderers, format_suffix=None):
        renderer = renderers[0]
        return renderer, renderer.media_type
