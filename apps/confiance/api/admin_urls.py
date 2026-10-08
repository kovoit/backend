from django.urls import path

from apps.confiance.api import views

urlpatterns = [
    path("signalements/", views.SignalementAdminListeVue.as_view(), name="admin-signalements"),
    path(
        "signalements/<uuid:pk>/traiter/",
        views.SignalementTraiterVue.as_view(),
        name="admin-signalement-traiter",
    ),
]
