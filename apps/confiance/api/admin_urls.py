from django.urls import path

from apps.confiance.api import admin_views as views

urlpatterns = [
    path("signalements/", views.SignalementAdminListeVue.as_view(), name="admin-signalements"),
    path(
        "signalements/<uuid:pk>/",
        views.SignalementAdminDetailVue.as_view(),
        name="admin-signalement-detail",
    ),
    path(
        "signalements/<uuid:pk>/traiter/",
        views.SignalementTraiterVue.as_view(),
        name="admin-signalement-traiter",
    ),
]
