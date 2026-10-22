from django.urls import path

from apps.audit.api import views
from apps.audit.api.export import ExportVue

urlpatterns = [
    path("audit/evenements/", views.EvenementListeVue.as_view(), name="admin-audit-evenements"),
    path(
        "audit/evenements/<uuid:pk>/",
        views.EvenementDetailVue.as_view(),
        name="admin-audit-evenement",
    ),
    path("audit/flux/", views.FluxVue.as_view(), name="admin-audit-flux"),
    path("audit/export/", ExportVue.as_view(), name="admin-audit-export"),
    path("audit/statistiques/", views.StatistiquesVue.as_view(), name="admin-audit-statistiques"),
]
