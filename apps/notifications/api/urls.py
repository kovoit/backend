from django.urls import path

from apps.notifications.api import liste
from apps.notifications.api.views import AppareilDetailVue, AppareilListeVue

urlpatterns = [
    path("notifications/", liste.NotificationListeVue.as_view(), name="notifications"),
    path("notifications/non-lues/", liste.NonLuesVue.as_view(), name="notifications-non-lues"),
    path("notifications/tout-lire/", liste.ToutLireVue.as_view(), name="notifications-tout-lire"),
    path("notifications/<uuid:pk>/lue/", liste.MarquerLueVue.as_view(), name="notification-lue"),
    path("notifications/appareils/", AppareilListeVue.as_view(), name="appareils"),
    path(
        "notifications/appareils/<str:jeton>/",
        AppareilDetailVue.as_view(),
        name="appareil-detail",
    ),
]
