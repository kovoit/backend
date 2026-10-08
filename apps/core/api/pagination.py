"""Pagination : la liste paginée est placée dans `reponse` de l'enveloppe."""

from rest_framework.pagination import PageNumberPagination

from apps.core.api.reponses import succes


class Pagination(PageNumberPagination):
    page_size_query_param = "taille"
    max_page_size = 100
    message = "Liste récupérée."

    def get_paginated_response(self, data):
        return succes(
            self.message,
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            },
        )

    def get_paginated_response_schema(self, schema):
        lien = {"type": "string", "format": "uri", "nullable": True}
        return {
            "type": "object",
            "required": ["count", "results"],
            "properties": {
                "count": {"type": "integer"},
                "next": lien,
                "previous": lien,
                "results": schema,
            },
        }


def reponse_paginee(request, queryset, serializer_class, message: str, vue=None):
    """Pagine un queryset (fourni par un service) et renvoie la réponse enveloppée."""
    paginateur = Pagination()
    paginateur.message = message
    page = paginateur.paginate_queryset(queryset, request, view=vue)
    data = serializer_class(page, many=True, context={"request": request}).data
    return paginateur.get_paginated_response(data)
