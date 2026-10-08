from django.urls import path

from apps.reservations.api import actions, views

urlpatterns = [
    path("reservations/", views.ReservationListeVue.as_view(), name="reservations"),
    path("reservations/<uuid:pk>/", views.ReservationDetailVue.as_view(), name="reservation"),
    path("reservations/<uuid:pk>/accepter/", actions.AccepterVue.as_view(), name="accepter"),
    path("reservations/<uuid:pk>/refuser/", actions.RefuserVue.as_view(), name="refuser"),
    path("reservations/<uuid:pk>/annuler/", actions.AnnulerVue.as_view(), name="annuler"),
    path(
        "reservations/<uuid:pk>/code-depart/", actions.CodeDepartVue.as_view(), name="code-depart"
    ),
    path("reservations/<uuid:pk>/absent/", actions.AbsentVue.as_view(), name="absent"),
    path(
        "reservations/<uuid:pk>/confirmer-arrivee/",
        actions.ConfirmerArriveeVue.as_view(),
        name="confirmer-arrivee",
    ),
    path(
        "trajets/<uuid:pk>/reservations/",
        views.TrajetReservationsVue.as_view(),
        name="trajet-reservations",
    ),
]
