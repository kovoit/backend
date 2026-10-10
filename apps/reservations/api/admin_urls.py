from django.urls import path

from apps.reservations.api.admin_views import ReservationAdminDetailVue, ReservationAdminListeVue

urlpatterns = [
    path("reservations/", ReservationAdminListeVue.as_view(), name="admin-reservations"),
    path(
        "reservations/<uuid:pk>/",
        ReservationAdminDetailVue.as_view(),
        name="admin-reservation-detail",
    ),
]
