from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN
from apps.audit.api.serializers import FiltresSerializer
from apps.audit.services.export import exporter_csv


class ExportVue(APIView):
    """CSV (séparateur « ; », UTF-8 avec BOM pour Excel). Au plus 10 000 lignes : au-delà,
    l'en-tête X-Export-Tronque vaut 1 et il faut resserrer les filtres."""

    permission_classes = ADMIN

    @extend_schema(
        tags=["admin - audit"],
        summary="Exporter le journal filtré (CSV)",
        parameters=[FiltresSerializer],
        responses={(200, "text/csv"): OpenApiTypes.STR},
    )
    def get(self, request):
        entree = FiltresSerializer(data=request.query_params)
        entree.is_valid(raise_exception=True)
        contenu, lignes, tronque = exporter_csv(entree.validated_data)
        reponse = HttpResponse("﻿" + contenu, content_type="text/csv; charset=utf-8")
        nom = f"journal-audit-{timezone.localdate():%Y-%m-%d}.csv"
        reponse["Content-Disposition"] = f'attachment; filename="{nom}"'
        reponse["X-Export-Lignes"] = str(lignes)
        reponse["X-Export-Tronque"] = "1" if tronque else "0"
        return reponse
