from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.api.vues_erreurs import page_introuvable

# API de l'application mobile : /api/v1/...
API_APPLICATION = [
    "apps.core.api.urls",
    "apps.accounts.api.urls",
    "apps.kyc.api.urls",
    "apps.vehicules.api.urls",
    "apps.trajets.api.urls",
    "apps.reservations.api.urls",
    "apps.confiance.api.urls",
    "apps.partage.api.urls",
    "apps.portefeuille.api.urls",
    "apps.notifications.api.urls",
    "apps.dashboard.api.urls",
]

# API de l'admin React : /api/v1/admin/...
API_ADMIN = [
    "apps.accounts.api.admin_urls",
    "apps.kyc.api.admin_urls",
    "apps.trajets.api.admin_urls",
    "apps.reservations.api.admin_urls",
    "apps.confiance.api.admin_urls",
    "apps.dashboard.api.admin_urls",
]

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="docs"), name="racine"),
    path("django-admin/", admin.site.urls),
    path("api/v1/auth/admin/", include("apps.accounts.api.admin_auth_urls")),
    path("api/v1/admin/parametres/", include("apps.parametres.api.urls")),
    *[path("api/v1/admin/", include(module)) for module in API_ADMIN],
    *[path("api/v1/", include(module)) for module in API_APPLICATION],
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    # Toute URL d'API inconnue répond en JSON (enveloppe failed), même avec DEBUG=True
    re_path(r"^api/", page_introuvable),
]

handler404 = "apps.core.api.vues_erreurs.page_introuvable"
handler500 = "apps.core.api.vues_erreurs.erreur_serveur"
