from django.urls import path

from apps.confiance.api import views

urlpatterns = [
    path("utilisateurs/<uuid:pk>/", views.ProfilPublicVue.as_view(), name="profil-public"),
    path("reservations/<uuid:pk>/note/", views.NoteVue.as_view(), name="reservation-note"),
    path(
        "reservations/<uuid:pk>/signalement/",
        views.SignalementVue.as_view(),
        name="reservation-signalement",
    ),
]
