from django.urls import path

from apps.reservations.api.views import ReservationAdminListeVue

urlpatterns = [
    path("reservations/", ReservationAdminListeVue.as_view(), name="admin-reservations"),
]
