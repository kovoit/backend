from django.urls import path

from apps.notifications.api.views import AppareilDetailVue, AppareilListeVue

urlpatterns = [
    path("notifications/appareils/", AppareilListeVue.as_view(), name="appareils"),
    path(
        "notifications/appareils/<str:jeton>/",
        AppareilDetailVue.as_view(),
        name="appareil-detail",
    ),
]
